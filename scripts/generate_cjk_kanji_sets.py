#!/usr/bin/env python3
#
# Copyright © 2020-present Peter M. Stahl pemistahl@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generates the kanji sets that separate Chinese from Japanese Han-only text.

The sets are derived from the Unicode Han Database (Unihan), not from the
bundled language models: the Chinese model contains traditional characters
only and the Japanese model contains simplified Chinese characters, so the
models cannot tell which characters the two languages genuinely share.

Usage:
    curl -sSLO https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip
    unzip Unihan.zip -d unihan
    python3 scripts/generate_cjk_kanji_sets.py unihan

Writes:
    src/data/japanese_usable_kanji.txt
        Kanji that occur in Japanese text: the official Jōyō and Jinmeiyō
        lists, plus the JIS X 0208 kanji that Japanese has no modern
        replacement for (e.g. 嘘, 罠, 鹸), plus EXTRA_JAPANESE_ONLY and
        EXTRA_SHARED. Old forms that Japanese replaced, such as 學 (now 学) or
        國 (now 国), are excluded, so they keep counting as evidence for
        Chinese.
    src/data/japanese_unique_kanji.txt
        Jōyō and Jinmeiyō kanji that are in neither the simplified (通用规范汉字表)
        nor the traditional (Big5) Chinese standard, e.g. 帯, 図, 峠, plus
        EXTRA_JAPANESE_ONLY.
"""

import sys
from collections import defaultdict
from pathlib import Path

# Characters of the Han script that the official lists leave out:
# the iteration marks 々 and 〻 and the closing mark 〆, which only Japanese
# uses, and variants used in Japanese personal and place names (髙橋, 山﨑,
# 𠮷野家) that are in neither Chinese standard and not in the Chinese test
# data. Without them, 人々 or 髙橋 would count as Chinese.
EXTRA_JAPANESE_ONLY = set("々〆〻髙﨑嵜𠮷濵邉")

# The ideographic zero, used in both languages (二〇二六年).
EXTRA_SHARED = set("〇")

VARIANT_FIELDS = {
    "kSimplifiedVariant",
    "kZVariant",
    "kSemanticVariant",
    "kSpecializedSemanticVariant",
}


def code_point(token):
    return chr(int(token.split("<")[0][2:], 16))


def read_fields(path, wanted):
    values = defaultdict(dict)
    with open(path, encoding="utf-8") as file:
        for line in file:
            if line.startswith("#") or not line.strip():
                continue
            cp, field, value = line.rstrip("\n").split("\t", 2)
            if field in wanted:
                values[field][code_point(cp)] = value
    return values


def main(unihan_dir):
    unihan = Path(unihan_dir)
    mappings = read_fields(
        unihan / "Unihan_OtherMappings.txt",
        {"kJoyoKanji", "kJinmeiyoKanji", "kJis0", "kTGH", "kBigFive"},
    )
    variant_fields = read_fields(unihan / "Unihan_Variants.txt", VARIANT_FIELDS)

    variants = defaultdict(set)
    for field in variant_fields.values():
        for character, value in field.items():
            variants[character].update(code_point(token) for token in value.split())

    joyo = set(mappings["kJoyoKanji"])
    # Jinmeiyō entries with a value like "2010:U+4E57" are old variant forms
    # that are only permitted in personal names, so they are left out.
    jinmeiyo = {c for c, v in mappings["kJinmeiyoKanji"].items() if ":" not in v}
    official = joyo | jinmeiyo

    jis = set(mappings["kJis0"])
    old_forms = {c for c in jis - official if variants[c] & official}
    usable = official | (jis - old_forms)

    chinese = set(mappings["kTGH"]) | set(mappings["kBigFive"])
    unique = (official - chinese) | EXTRA_JAPANESE_ONLY
    usable |= EXTRA_JAPANESE_ONLY | EXTRA_SHARED

    data = Path(__file__).resolve().parent.parent / "src" / "data"
    data.mkdir(exist_ok=True)
    (data / "japanese_usable_kanji.txt").write_text("".join(sorted(usable)), encoding="utf-8")
    (data / "japanese_unique_kanji.txt").write_text("".join(sorted(unique)), encoding="utf-8")
    print(f"japanese_usable_kanji.txt: {len(usable)} kanji")
    print(f"japanese_unique_kanji.txt: {len(unique)} kanji")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
