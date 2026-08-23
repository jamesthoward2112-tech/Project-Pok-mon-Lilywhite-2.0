#!/usr/bin/env python3
# Project Pokémon Lilywhite 2.0
# M0/M1 source patcher for rh-hideout/pokeemerald-expansion
# Pinned ref: expansion/1.16.3
#
# This script only edits source text. It deliberately fails if the expected
# pinned-source text is not present instead of guessing.

from pathlib import Path
import argparse

PINNED_REF = "expansion/1.16.3"

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)

def patch_file(path, fn):
    if not path.exists():
        raise FileNotFoundError(path)
    original = path.read_text(encoding="utf-8")
    changed = fn(original)
    if changed == original:
        raise RuntimeError(f"No changes made to {path}")
    path.write_text(changed, encoding="utf-8")
    print(f"patched {path}")

def get_section(text, header):
    start = text.find(header)
    if start < 0:
        raise RuntimeError(f"Missing section: {header}")
    next_pos = text.find("\n=== ", start + len(header))
    if next_pos < 0:
        next_pos = len(text)
    return start, next_pos, text[start:next_pos]

def patch_first_mon_in_party_section(text, trainer_label, species):
    header = f"=== {trainer_label} ==="
    s, e, block = get_section(text, header)
    lines = block.splitlines()
    try:
        blank = lines.index("", 1)
    except ValueError:
        raise RuntimeError(f"{trainer_label}: no metadata/species separator")
    idx = blank + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines):
        raise RuntimeError(f"{trainer_label}: no Pokémon found")
    lines[idx] = species
    new_block = "\n".join(lines)
    if block.endswith("\n"):
        new_block += "\n"
    return text[:s] + new_block + text[e:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="Path to pokeemerald-expansion checkout")
    ap.add_argument(
        "--experimental-r-run",
        action="store_true",
        help="Also install Lilywhite forced R-to-run. Keep off for first engine-proof compile.",
    )
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    # 1) Stable QoL config changes verified against expansion/1.16.3.
    item_h = repo / "include/config/item.h"
    def patch_item(text):
        text = replace_once(
            text,
            "#define I_USE_EVO_HELD_ITEMS_FROM_BAG   FALSE",
            "#define I_USE_EVO_HELD_ITEMS_FROM_BAG   TRUE",
            "direct-use evolution held items",
        )
        text = replace_once(
            text,
            "#define I_REUSABLE_TMS          FALSE",
            "#define I_REUSABLE_TMS          TRUE",
            "reusable TMs",
        )
        return text
    patch_file(item_h, patch_item)

    battle_h = repo / "include/config/battle.h"
    def patch_battle_config(text):
        text = replace_once(
            text,
            "#define B_RUN_TRAINER_BATTLE                TRUE",
            "#define B_RUN_TRAINER_BATTLE                FALSE",
            "disable trainer-battle running",
        )
        text = replace_once(
            text,
            "#define B_MOVE_DESCRIPTION_BUTTON           L_BUTTON",
            "#define B_MOVE_DESCRIPTION_BUTTON           START_BUTTON",
            "move-description button",
        )
        text = replace_once(
            text,
            "#define B_LAST_USED_BALL_BUTTON     R_BUTTON",
            "#define B_LAST_USED_BALL_BUTTON     L_BUTTON",
            "L = last-used Poké Ball",
        )
        return text
    patch_file(battle_h, patch_battle_config)

    # 2) Development Quickstart: fixed Harry / Sol.
    quick_cfg = repo / "include/config/quickstart.h"
    def patch_quick_cfg(text):
        return replace_once(
            text,
            "#define QUICKSTART_GENDER            GENDER_RANDOM",
            "#define QUICKSTART_GENDER            GENDER_MALE",
            "quickstart male protagonist",
        )
    patch_file(quick_cfg, patch_quick_cfg)

    quick_c = repo / "src/quickstart.c"
    def patch_quick_c(text):
        text = replace_once(
            text,
            'static const u8 sText_PlayerMale[] = _("RED");',
            'static const u8 sText_PlayerMale[] = _("HARRY");',
            "quickstart Harry",
        )
        text = replace_once(
            text,
            'static const u8 sText_PlayerFemale[] = _("LEAF");',
            'static const u8 sText_PlayerFemale[] = _("HARRY");',
            "quickstart female fallback",
        )
        text = replace_once(
            text,
            'static const u8 sText_Rival[] = _("BLUE");',
            'static const u8 sText_Rival[] = _("SOL");',
            "quickstart Sol",
        )
        return text
    patch_file(quick_c, patch_quick_c)

    # 3) Oak Lab: repurpose the Bulbasaur pedestal as Nidoran♂.
    #    PLAYER_STARTER_NUM remains 0, so vanilla routing stays structurally safe.
    lab = repo / "data/maps/PalletTown_ProfessorOaksLab_Frlg/scripts.inc"
    def patch_lab(text):
        label = "PalletTown_ProfessorOaksLab_EventScript_BulbasaurBall::"
        s = text.find(label)
        if s < 0:
            raise RuntimeError("Oak Lab: Bulbasaur pedestal script missing")
        e = text.find("\nPalletTown_ProfessorOaksLab_EventScript_ConfirmStarterChoice::", s)
        if e < 0:
            raise RuntimeError("Oak Lab: end of Bulbasaur pedestal script missing")
        block = text[s:e]
        block = replace_once(
            block,
            "setvar PLAYER_STARTER_SPECIES, SPECIES_BULBASAUR",
            "setvar PLAYER_STARTER_SPECIES, SPECIES_NIDORAN_M",
            "Nidoran male starter",
        )
        block = replace_once(
            block,
            "setvar RIVAL_STARTER_SPECIES, SPECIES_CHARMANDER",
            "setvar RIVAL_STARTER_SPECIES, SPECIES_PIKACHU",
            "Sol Pikachu starter display",
        )
        text = text[:s] + block + text[e:]

        text = replace_once(
            text,
            "msgbox PalletTown_ProfessorOaksLab_Text_OakChoosingBulbasaur, MSGBOX_YESNO",
            "msgbox Lilywhite_Text_OakChoosingNidoranM, MSGBOX_YESNO",
            "starter confirmation text hook",
        )

        nickname_block = (
            "\tmsgbox gText_NicknameThisPokemon, MSGBOX_YESNO\n"
            "\tgoto_if_eq VAR_RESULT, YES, EventScript_GiveNicknameToStarter\n"
            "\tgoto_if_eq VAR_RESULT, NO, PalletTown_ProfessorOaksLab_EventScript_RivalPicksStarter\n"
            "\tend\n"
        )
        nickname_replacement = (
            "\tgoto PalletTown_ProfessorOaksLab_EventScript_RivalPicksStarter\n"
            "\tend\n"
        )
        text = replace_once(
            text,
            nickname_block,
            nickname_replacement,
            "skip starter nickname prompt",
        )

        if "Lilywhite_Text_OakChoosingNidoranM:" not in text:
            text += (
                "\n@ Project Pokémon Lilywhite 2.0\n"
                "Lilywhite_Text_OakChoosingNidoranM:\n"
                '\t.string "So, {PLAYER}, you want NIDORAN♂?\\n"\n'
                '\t.string "This POKéMON is full of potential.$"\n'
            )
        return text
    patch_file(lab, patch_lab)

    # 4) Sol uses Pikachu in all Oak-Lab rival variants.
    trainers = repo / "src/data/trainers_frlg.party"
    def patch_trainers(text):
        for label in (
            "TRAINER_RIVAL_OAKS_LAB_CHARMANDER",
            "TRAINER_RIVAL_OAKS_LAB_BULBASAUR",
            "TRAINER_RIVAL_OAKS_LAB_SQUIRTLE",
        ):
            text = patch_first_mon_in_party_section(text, label, "Pikachu")
        return text
    patch_file(trainers, patch_trainers)

    # 5) Optional experimental R = forced wild escape.
    #    The first engine-proof compile should omit this, then add it in isolation.
    if args.experimental_r_run:
        controller = repo / "src/battle_controller_player.c"
        def patch_controller(text):
            include_anchor = '#include "test/battle.h"\n'
            text = replace_once(
                text,
                include_anchor,
                include_anchor + "\nextern bool8 gLilywhiteForcedRun;\n",
                "R-run extern",
            )
            anchor = (
                "    DoBounceEffect(battler, BOUNCE_HEALTHBOX, 7, 1);\n"
                "    DoBounceEffect(battler, BOUNCE_MON, 7, 1);\n"
            )
            forced = anchor + (
                "\n"
                "    // Lilywhite 2.0: unconditional escape shortcut in ordinary wild battles.\n"
                "    if (JOY_NEW(R_BUTTON)\n"
                "     && !(gBattleTypeFlags & (BATTLE_TYPE_TRAINER\n"
                "                            | BATTLE_TYPE_LINK\n"
                "                            | BATTLE_TYPE_RECORDED_LINK\n"
                "                            | BATTLE_TYPE_SAFARI)))\n"
                "    {\n"
                "        gLilywhiteForcedRun = TRUE;\n"
                "        PlaySE(SE_SELECT);\n"
                "        TryHideLastUsedBall();\n"
                "        BtlController_EmitTwoReturnValues(battler, B_COMM_TO_ENGINE, B_ACTION_RUN, 0);\n"
                "        BtlController_Complete(battler);\n"
                "        return;\n"
                "    }\n"
            )
            return replace_once(text, anchor, forced, "forced R-run input")
        patch_file(controller, patch_controller)

        main_c = repo / "src/battle_main.c"
        def patch_main(text):
            text = replace_once(
                text,
                "EWRAM_DATA u16 gLastUsedBall = 0;",
                "EWRAM_DATA u16 gLastUsedBall = 0;\n"
                "EWRAM_DATA bool8 gLilywhiteForcedRun = FALSE;",
                "forced R-run state",
            )
            sig = "static void BattleStartClearSetData(void)\n{"
            text = replace_once(
                text,
                sig,
                sig + "\n    gLilywhiteForcedRun = FALSE;",
                "forced R-run reset",
            )
            old = (
                "else if ((IsRunningFromBattleImpossible(battler) != BATTLE_RUN_SUCCESS\n"
                "                         && gBattleResources->bufferB[battler][1] == B_ACTION_RUN)\n"
                "                         || (FlagGet(WE_FLAG_NO_RUNNING) == TRUE && gBattleResources->bufferB[battler][1] == B_ACTION_RUN))"
            )
            new = (
                "else if (!gLilywhiteForcedRun\n"
                "                      && ((IsRunningFromBattleImpossible(battler) != BATTLE_RUN_SUCCESS\n"
                "                         && gBattleResources->bufferB[battler][1] == B_ACTION_RUN)\n"
                "                         || (FlagGet(WE_FLAG_NO_RUNNING) == TRUE && gBattleResources->bufferB[battler][1] == B_ACTION_RUN)))"
            )
            return replace_once(text, old, new, "forced R-run escape bypass")
        patch_file(main_c, patch_main)

        # Selection validation is only half of the run path: HandleAction_Run()
        # later calls TryRunFromBattle(), which can still fail on Speed/Arena Trap.
        # Patch that execution stage too so the R shortcut is truly unconditional.
        battle_util = repo / "src/battle_util.c"
        def patch_battle_util(text):
            include_anchor = '#include "battle_util.h"\n'
            text = replace_once(
                text,
                include_anchor,
                include_anchor + "\nextern bool8 gLilywhiteForcedRun;\n",
                "R-run battle_util extern",
            )
            old = (
                "        if (IsOnPlayerSide(gBattlerAttacker))\n"
                "        {\n"
                "            if (!TryRunFromBattle(gBattlerAttacker)) // failed to run away\n"
                "            {\n"
            )
            new = (
                "        if (IsOnPlayerSide(gBattlerAttacker))\n"
                "        {\n"
                "            if (gLilywhiteForcedRun)\n"
                "            {\n"
                "                // R shortcut: force a clean wild-battle exit.\n"
                "                gLilywhiteForcedRun = FALSE;\n"
                "                gCurrentTurnActionNumber = gBattlersCount;\n"
                "                gBattleOutcome = B_OUTCOME_RAN;\n"
                "            }\n"
                "            else if (!TryRunFromBattle(gBattlerAttacker)) // failed to run away\n"
                "            {\n"
            )
            return replace_once(text, old, new, "forced R-run action success")
        patch_file(battle_util, patch_battle_util)

    print()
    print("Lilywhite 2.0 M1 source changes applied.")
    print("Pinned upstream:", PINNED_REF)
    print("Compile with: make firered")
    if not args.experimental_r_run:
        print("R-to-run intentionally omitted from first engine-proof compile.")

if __name__ == "__main__":
    main()
