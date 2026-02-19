"""
ai_opponent.py  –  Claude-powered Durak AI for Uno-Urak

The AI receives a full, structured game-state snapshot and returns one of:
  { "action": "attack",  "card": "<key>",  "slot": <0-5> }
  { "action": "defend",  "atk_card": "<key>",  "def_card": "<key>" }
  { "action": "take" }
  { "action": "end_attack" }
  { "action": "choose_suit", "suit": "<clubs|diamonds|hearts|spades>" }

All communication is synchronous (called from a worker thread).
"""

import json
import urllib.request
import urllib.error
import random


# ── Expert AI system prompt ────────────────────────────────────────────────────

_SYSTEM = """You are a world-class Durak card-game AI.  You play ruthlessly and optimally.
Your goal is to empty your hand before the opponent does.  The loser is the last player
holding cards — called the "Durak" (fool).

─── CARD TYPES ───────────────────────────────────────────────────────────────
Normal cards  : ranks 6-A in four suits (clubs♣ diamonds♦ hearts♥ spades♠)
TRUMP suit    : any trump card beats any non-trump card of any rank.
                Within trump, higher rank still wins.
SKIP card     : defends against an attack of the SAME suit. Locks that rank for
                the rest of the round (attacker may NOT pile on with that rank).
REVERSE card  : defends against any card of the SAME suit. Immediately swaps
                attacker and defender roles.
WILD card     : defends against ANY attack card. Lets the defender choose the
                new trump suit — pick the suit you hold the most of.

─── TURN STRUCTURE ────────────────────────────────────────────────────────────
ATTACK phase  : Play one card to an empty field slot.  Then pile on with more
                cards of the SAME rank (up to 3 slots total).  After all attacks
                are beaten you must call end_attack to advance.
DEFENSE phase : Cover each attack card, or call take to take everything.

─── MASTER STRATEGY (follow this rigorously) ──────────────────────────────────

ATTACKING — make it as hard as possible for the opponent to defend:
1. Lead with cards whose rank already appears on the table so you can pile on.
2. Attack with your HIGHEST non-trump cards first; save low trumps as a last resort.
3. If you have a Skip of the correct suit, plan to play the matching rank so the
   opponent cannot pile further after the Skip locks it.
4. Pile on aggressively: after a successful first attack, pile on with ALL
   matching ranks you hold so the opponent must defend multiple cards at once.
5. If opponent hand is small (≤3 cards), pile on with every legal card you have
   to force them to take or exhaust their hand.
6. Use Reverse sparingly on attack — it is far stronger on defense.
7. If deck is empty and you have more cards than opponent, attack with the
   highest-rank cards to dump your hand quickly.

DEFENDING — survive cheaply, never waste good cards:
1. Prefer to beat an attack with the CHEAPEST valid card (lowest rank, non-trump
   if possible).
2. Never use a trump to beat a non-trump unless you have no alternative.
3. Play a REVERSE card whenever it legally beats the attack — it swaps roles and
   lets you attack instead.  This is extremely powerful.
4. Play a SKIP card to lock a rank when you are at risk of being pile-attacked
   with that rank (opponent holds multiple of it).
5. TAKE (give up) only if: defending would cost ≥2 trump cards, OR defending
   would leave you with zero or one non-trump card in a long game.
6. If you TAKE, immediately use cards from the taken pile to attack next turn —
   do not hoard them.

TRUMP MANAGEMENT:
• Treat trump cards as precious; use them only when necessary.
• When choosing suit after a Wild, pick the suit you hold the MOST of in hand
  (maximises future coverage).  Tie-break: the suit opponent is weakest in.

TAKEN PILE STRATEGY:
• Cards in your taken pile count as part of your hand for attacks.
• After taking, lead with taken-pile cards (especially high non-trump) to shed
  them fast before the opponent can count your hand size.

ENDGAME (deck empty):
• If your hand + taken pile ≤ 3 cards total, play aggressively — dump everything.
• If opponent has 1 card, attack with your strongest trump to prevent them winning.

─── OUTPUT FORMAT ─────────────────────────────────────────────────────────────
Respond with ONLY a single JSON object.  No prose, no markdown, no explanation.
Choose EXACTLY one of these shapes:

  {"action":"attack",  "card":"<key>", "slot":<0|1|2|3|4|5>}
  {"action":"defend",  "atk_card":"<key>", "def_card":"<key>"}
  {"action":"take"}
  {"action":"end_attack"}
  {"action":"choose_suit", "suit":"<clubs|diamonds|hearts|spades>"}

"key" is the exact image-dictionary key from the game (e.g. "aceH", "skipC",
"reverseD", "wild", "tenS").  Only output keys that appear in your legal moves.
"""


# ── State serialiser ───────────────────────────────────────────────────────────

def build_state_prompt(rules, ask_wild=False):
    """Convert a DurakRules instance into a readable prompt for the AI."""

    def card_info(k):
        """Human-readable card description."""
        from ai_opponent import _parse_key_local
        suit, rank = _parse_key_local(k)
        trump_mark = "★TRUMP" if suit == rules.trump_suit else ""
        return f"{k}({rank} of {suit}{' ' + trump_mark if trump_mark else ''})"

    ai_hand_desc   = [card_info(k) for k in rules.opp_hand]
    ai_taken_desc  = [card_info(k) for k in rules.opp_taken]
    plr_hand_size  = len(rules.hand)
    plr_taken_size = len(rules.player_taken)
    table_desc = []
    for i, slot in enumerate(rules.table):
        if slot is None:
            table_desc.append(f"slot{i}:empty")
        else:
            atk, dfn = slot
            table_desc.append(f"slot{i}:atk={card_info(atk)} def={'(none)' if dfn is None else card_info(dfn)}")

    lines = [
        f"TRUMP SUIT: {rules.trump_suit}  (trump card key: {rules.trump_key})",
        f"DECK remaining: {len(rules.remaining)} cards",
        f"PHASE: {rules.phase}",
        f"You are: {'ATTACKER' if rules.attacker == 'opponent' else 'DEFENDER'}",
        "",
        f"YOUR HAND ({len(rules.opp_hand)} cards): {', '.join(ai_hand_desc) if ai_hand_desc else '(empty)'}",
        f"YOUR TAKEN PILE ({len(rules.opp_taken)} cards): {', '.join(ai_taken_desc) if ai_taken_desc else '(empty)'}",
        "",
        f"OPPONENT HAND SIZE: {plr_hand_size}  TAKEN PILE SIZE: {plr_taken_size}",
        "",
        "FIELD TABLE:",
    ] + [f"  {d}" for d in table_desc]

    if ask_wild:
        lines += [
            "",
            "You just played a WILD card.  Choose the new trump suit.",
            "Return: {\"action\":\"choose_suit\", \"suit\":\"<clubs|diamonds|hearts|spades>\"}",
        ]
    elif rules.phase == 'attack' and rules.attacker == 'opponent':
        legal = rules.valid_attack_cards()
        all_beaten = (any(s is not None for s in rules.table) and
                      all(s[1] is not None for s in rules.table if s is not None))
        lines += [
            "",
            f"LEGAL ATTACK CARDS: {', '.join(legal) if legal else '(none — you must end attack)'}",
            f"CAN END ATTACK: {'yes' if all_beaten and any(s is not None for s in rules.table) else 'no'}",
            "",
            "Choose: attack with a card, or end_attack if all cards are beaten and you want to finish.",
        ]
    elif rules.phase == 'defense' and rules.defender == 'opponent':
        unbeaten = [(i, s[0]) for i, s in enumerate(rules.table) if s is not None and s[1] is None]
        def_options = {}
        for i, atk_k in unbeaten:
            valid = rules.valid_defense_for(atk_k)
            def_options[atk_k] = list(valid)
        lines += [
            "",
            "UNBEATEN ATTACKS (you must cover all or TAKE):",
        ]
        for atk_k, options in def_options.items():
            lines.append(f"  {card_info(atk_k)}  →  can beat with: {', '.join(options) if options else '(nothing)' }")
        lines += [
            "",
            "Choose: defend each attack, or take.",
        ]

    return "\n".join(lines)


# ── Local card parser (mirrors game logic, no pygame dependency) ──────────────

_RANK_NAMES_LOCAL = {
    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
    'jack': 'J', 'queen': 'Q', 'king': 'K', 'ace': 'A'
}
_SUIT_SUFFIX_LOCAL = {'C': 'clubs', 'D': 'diamonds', 'H': 'hearts', 'S': 'spades'}
_SKIP_SUIT_LOCAL   = {'skipC': 'clubs', 'skipD': 'diamonds', 'skipH': 'hearts', 'skipS': 'spades'}
_REVERSE_SUIT_LOCAL = {'reverseC': 'clubs', 'reverseD': 'diamonds', 'reverseH': 'hearts', 'reverseS': 'spades'}


def _parse_key_local(key):
    if key == 'wild':      return ('wild', 'WILD')
    if key in _SKIP_SUIT_LOCAL:    return (_SKIP_SUIT_LOCAL[key], 'SKIP')
    if key in _REVERSE_SUIT_LOCAL: return (_REVERSE_SUIT_LOCAL[key], 'REVERSE')
    low = key.lower()
    for name, rank in _RANK_NAMES_LOCAL.items():
        if low.startswith(name):
            return _SUIT_SUFFIX_LOCAL[key[len(name):]], rank
    raise ValueError(f"Cannot parse: {key!r}")


# ── Fallback heuristic AI (used if API unavailable) ───────────────────────────

_RANK_ORDER_LOCAL = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def _rank_strength(key, trump_suit):
    suit, rank = _parse_key_local(key)
    if rank in ('SKIP', 'REVERSE', 'WILD'): return 50
    base = _RANK_ORDER_LOCAL.index(rank)
    return base + (100 if suit == trump_suit else 0)


def heuristic_action(rules, ask_wild=False):
    """
    Strong rule-based fallback AI.
    Returns the same dict format as the API AI.
    """
    trump = rules.trump_suit

    if ask_wild:
        # Pick the suit we hold the most of
        from collections import Counter
        c = Counter()
        for k in rules.opp_hand + rules.opp_taken:
            suit, rank = _parse_key_local(k)
            if rank not in ('SKIP', 'REVERSE', 'WILD'):
                c[suit] += 1
        best = max(c, key=c.get) if c else 'clubs'
        return {"action": "choose_suit", "suit": best}

    if rules.phase == 'attack' and rules.attacker == 'opponent':
        legal = list(rules.valid_attack_cards())
        if not legal:
            return {"action": "end_attack"}

        # Check if we can end attack (all beaten)
        occupied = [s for s in rules.table if s is not None]
        all_beaten = bool(occupied) and all(s[1] is not None for s in occupied)
        if all_beaten and occupied:
            # Decide: should we pile on more or end?
            # If opponent hand is small, end to swap roles
            if len(rules.hand) + len(rules.player_taken) <= 3:
                return {"action": "end_attack"}

        # Find first empty slot
        empty_slots = [i for i, s in enumerate(rules.table) if s is None]
        if not empty_slots:
            return {"action": "end_attack"}

        # Sort: prefer non-trump, higher rank first (to dump strong non-trump)
        legal_sorted = sorted(legal, key=lambda k: _rank_strength(k, trump), reverse=True)
        # Actually prefer mid-rank non-trump first, save trump
        non_trump = [k for k in legal_sorted if _parse_key_local(k)[0] != trump]
        trump_cards = [k for k in legal_sorted if _parse_key_local(k)[0] == trump]
        ordered = non_trump + trump_cards

        chosen = ordered[0] if ordered else legal_sorted[0]
        return {"action": "attack", "card": chosen, "slot": empty_slots[0]}

    elif rules.phase == 'defense' and rules.defender == 'opponent':
        # Find all unbeaten attacks
        unbeaten = [(i, s[0]) for i, s in enumerate(rules.table) if s is not None and s[1] is None]
        if not unbeaten:
            return {"action": "end_attack"}

        # Try to defend cheaply — pick weakest defender for strongest attack
        # Sort unbeaten by attack strength desc so we plan hardest first
        unbeaten_sorted = sorted(unbeaten, key=lambda x: _rank_strength(x[1], trump), reverse=True)

        used = set()
        plan = []
        for _, atk_k in unbeaten_sorted:
            options = [k for k in rules.valid_defense_for(atk_k) if k not in used]
            if not options:
                # Cannot defend — must take
                return {"action": "take"}
            # Cheapest defender (non-trump preferred, lowest rank)
            non_trump_opts = [k for k in options if _parse_key_local(k)[0] != trump]
            trump_opts = [k for k in options if _parse_key_local(k)[0] == trump]
            # Prefer Reverse (role-swap is powerful)
            reverse_opts = [k for k in options if _parse_key_local(k)[1] == 'REVERSE']
            if reverse_opts:
                chosen_def = min(reverse_opts, key=lambda k: _rank_strength(k, trump))
            elif non_trump_opts:
                chosen_def = min(non_trump_opts, key=lambda k: _rank_strength(k, trump))
            elif trump_opts:
                # Only use trump if attack is also strong or is trump
                atk_suit, atk_rank = _parse_key_local(atk_k)
                if _rank_strength(atk_k, trump) >= 5 or atk_suit == trump:
                    chosen_def = min(trump_opts, key=lambda k: _rank_strength(k, trump))
                else:
                    return {"action": "take"}  # Too expensive to use trump on weak card
            else:
                return {"action": "take"}
            plan.append((atk_k, chosen_def))
            used.add(chosen_def)

        # Return first planned defense (game loop will call us again for next)
        if plan:
            atk_k, def_k = plan[0]
            return {"action": "defend", "atk_card": atk_k, "def_card": def_k}

    return {"action": "end_attack"}


# ── Anthropic API call ─────────────────────────────────────────────────────────

def call_claude_api(api_key: str, state_prompt: str, model: str = "claude-haiku-4-5-20251001") -> dict:
    """
    Call the Anthropic messages API synchronously.
    Returns a parsed action dict, or raises on error.
    Uses Haiku for speed; falls back to heuristic on any error.
    """
    payload = {
        "model": model,
        "max_tokens": 256,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": state_prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = ""
    for block in body.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    # Strip any accidental markdown fences
    text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    return json.loads(text)


# ── Public entry point ─────────────────────────────────────────────────────────

def get_ai_action(rules, api_key: str | None, ask_wild: bool = False) -> dict:
    """
    Main entry point called from the game loop (in a worker thread).
    Returns an action dict.  Never raises — falls back to heuristic on error.
    """
    # Always try heuristic first as a sanity reference,
    # but use the API when a key is provided.
    if api_key:
        try:
            prompt = build_state_prompt(rules, ask_wild=ask_wild)
            action = call_claude_api(api_key, prompt)
            # Validate the returned action makes sense
            validated = _validate_action(action, rules, ask_wild)
            if validated:
                return validated
            # Fall through to heuristic if validation fails
        except Exception as e:
            print(f"[AI] API error ({type(e).__name__}: {e}), using heuristic.")

    return heuristic_action(rules, ask_wild=ask_wild)


def _validate_action(action: dict, rules, ask_wild: bool) -> dict | None:
    """
    Validate that the AI's chosen action is actually legal.
    Returns the action if valid, None otherwise.
    """
    a = action.get("action")

    if ask_wild:
        if a == "choose_suit" and action.get("suit") in ("clubs", "diamonds", "hearts", "spades"):
            return action
        return None

    if a == "end_attack":
        occupied = [s for s in rules.table if s is not None]
        all_beaten = bool(occupied) and all(s[1] is not None for s in occupied)
        if rules.phase == 'attack' and all_beaten:
            return action
        # Also valid if no legal attacks available
        if rules.phase == 'attack' and not rules.valid_attack_cards():
            return action
        return None

    if a == "attack":
        card = action.get("card")
        slot = action.get("slot")
        if card is None or slot is None: return None
        if card not in rules.valid_attack_cards(): return None
        if not (0 <= slot <= 5): return None
        if rules.table[slot] is not None: return None
        return action

    if a == "defend":
        atk = action.get("atk_card")
        def_ = action.get("def_card")
        if atk is None or def_ is None: return None
        if def_ not in rules.valid_defense_for(atk): return None
        # Make sure atk_card is actually unbeaten on the table
        found = any(s is not None and s[0] == atk and s[1] is None for s in rules.table)
        if not found: return None
        return action

    if a == "take":
        if rules.phase == "defense":
            return action
        return None

    return None
