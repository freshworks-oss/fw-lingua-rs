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

//! Runs the `augment` and `unique-update` modes of the `build_language_models`
//! binary against a temporary copy of the repository layout.

use std::fs;
use std::path::Path;
use std::process::{Command, Output};

use tempfile::{TempDir, tempdir};

const CORPUS: &str = "saya tidak tahu apa yang terjadi\nkami pergi ke pasar pagi ini\n";

fn build_language_models(args: &[&str]) -> Output {
    let output = Command::new(env!("CARGO_BIN_EXE_build_language_models"))
        .args(args)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    output
}

fn path_str(path: &Path) -> &str {
    path.to_str().unwrap()
}

/// A repository root holding an Indonesian model built from `CORPUS`.
fn repo_with_small_indonesian_model() -> (TempDir, TempDir) {
    let corpus_dir = tempdir().unwrap();
    let corpus_file = corpus_dir.path().join("corpus.txt");
    fs::write(&corpus_file, CORPUS).unwrap();

    let repo = tempdir().unwrap();
    build_language_models(&["model", "id", path_str(&corpus_file), path_str(repo.path())]);
    (repo, corpus_dir)
}

fn model_file(repo: &Path, code: &str) -> std::path::PathBuf {
    repo.join("language-models")
        .join(code)
        .join("models")
        .join("ngrams.fst")
}

#[test]
fn test_augment_mode_retrains_the_model() {
    let (repo, corpus_dir) = repo_with_small_indonesian_model();
    let original_model = fs::read(model_file(repo.path(), "id")).unwrap();
    let new_corpus_file = corpus_dir.path().join("new_corpus.txt");
    fs::write(&new_corpus_file, "gue nggak tahu nih\ngue nggak tahu nih\n").unwrap();

    let output = build_language_models(&[
        "augment",
        "id",
        path_str(&new_corpus_file),
        path_str(repo.path()),
        "2",
        "2",
    ]);

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("weight=2, min_new_ngram_count=2"),
        "{stdout}"
    );
    assert!(stdout.contains("unique-update"), "{stdout}");
    assert_ne!(
        fs::read(model_file(repo.path(), "id")).unwrap(),
        original_model
    );
}

#[test]
fn test_augment_mode_with_weight_zero_keeps_the_model() {
    let (repo, corpus_dir) = repo_with_small_indonesian_model();
    let original_model = fs::read(model_file(repo.path(), "id")).unwrap();

    build_language_models(&[
        "augment",
        "id",
        path_str(&corpus_dir.path().join("corpus.txt")),
        path_str(repo.path()),
        "0",
    ]);

    assert_eq!(
        fs::read(model_file(repo.path(), "id")).unwrap(),
        original_model
    );
}

#[test]
fn test_unique_update_mode_writes_the_changed_unique_ngrams() {
    // Measured against a much smaller previous model, nearly all of the shipped
    // Indonesian model counts as gained, so unique ngrams change.
    let (previous_repo, _corpus_dir) = repo_with_small_indonesian_model();
    let output_repo = tempdir().unwrap();

    let output = build_language_models(&[
        "unique-update",
        "id",
        path_str(previous_repo.path()),
        path_str(output_repo.path()),
    ]);

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("Updated id/models/unique-ngrams.fst"),
        "{stdout}"
    );
    let unique_ngrams_file = output_repo
        .path()
        .join("language-models/id/models/unique-ngrams.fst");
    assert!(
        fst::Set::new(fs::read(unique_ngrams_file).unwrap())
            .unwrap()
            .len()
            > 0
    );
}

#[test]
fn test_unique_update_mode_with_unchanged_models_writes_nothing() {
    let output_repo = tempdir().unwrap();

    let output = build_language_models(&[
        "unique-update",
        "id,ms",
        env!("CARGO_MANIFEST_DIR"),
        path_str(output_repo.path()),
    ]);

    assert!(!String::from_utf8_lossy(&output.stdout).contains("Updated"));
    assert!(!output_repo.path().join("language-models").exists());
}

#[test]
fn test_mostcommon_mode_writes_the_most_common_ngrams() {
    let (repo, corpus_dir) = repo_with_small_indonesian_model();

    build_language_models(&[
        "mostcommon",
        "ms",
        path_str(&corpus_dir.path().join("corpus.txt")),
        path_str(repo.path()),
    ]);

    let bytes = fs::read(
        repo.path()
            .join("language-models/ms/models/mostcommon-ngrams.fst"),
    )
    .unwrap();
    assert!(fst::Set::new(bytes).unwrap().len() > 0);
}

#[test]
fn test_unknown_mode_fails() {
    let output = Command::new(env!("CARGO_BIN_EXE_build_language_models"))
        .args(["translate", "id", "corpus.txt"])
        .output()
        .unwrap();

    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("unknown mode: translate"));
}
