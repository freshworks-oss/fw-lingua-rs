/*
 * Copyright © 2020-present Peter M. Stahl pemistahl@gmail.com
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#![cfg(not(target_family = "wasm"))]

//! Regression tests for texts that were detected wrongly before the
//! Indonesian and Malay models were retrained on colloquial text, and
//! before texts under 300 letters were scored on all ngram lengths.

use lingua::{Language, LanguageDetector, LanguageDetectorBuilder};
use std::sync::LazyLock;

static DETECTOR: LazyLock<LanguageDetector> =
    LazyLock::new(|| LanguageDetectorBuilder::from_all_languages().build());

fn letter_count(text: &str) -> usize {
    text.chars().filter(|c| c.is_alphabetic()).count()
}

#[test]
fn test_text_between_120_and_300_letters_is_scored_on_all_ngram_lengths() {
    // Scored on trigrams alone, "gos" (a common Spanish ending) and the
    // names outweighed the rest, and this was detected as Spanish.
    let text = "GOS: Prio 1 Descartes EDI bericht verkeer. Bel met standby AM_SAP \
                Er is een probleem gesignaleerd: Prio 1 Descartes EDI bericht \
                verkeer. Bel met standby AM_SAP";
    assert!((120..300).contains(&letter_count(text)));

    assert_eq!(DETECTOR.detect_language_of(text), Some(Language::Dutch));
}

#[test]
fn test_colloquial_indonesian_is_detected_as_indonesian() {
    // Detected as Malay (0.68) when both models only knew formal text.
    let text = "Ribet udah insert nggak dikeluarin ngurus ini susah nih susah ribet udah";

    assert_eq!(
        DETECTOR.detect_language_of(text),
        Some(Language::Indonesian)
    );
}

#[test]
fn test_formal_malay_is_still_detected_as_malay() {
    let text = "Kerajaan negeri akan memberi perhatian kepada pembangunan \
                infrastruktur di kawasan luar bandar pada tahun hadapan.";

    assert_eq!(DETECTOR.detect_language_of(text), Some(Language::Malay));
}
