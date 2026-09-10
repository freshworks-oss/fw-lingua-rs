use std::path::PathBuf;

use lingua::{
    Language, LanguageModelFilesWriter, MostCommonNgramsWriter, TestDataFilesWriter,
    UniqueNgramsWriter,
};

// Each arm is gated on its language feature, otherwise this binary fails to
// compile whenever the crate is built with a language subset, as in
// `cargo build --no-default-features --features german`.
fn lang_meta(code: &str) -> (Language, &'static str, &'static str) {
    match code {
        #[cfg(feature = "assamese")]
        "as" => (Language::Assamese, "as", "\\p{Bengali}"),
        #[cfg(feature = "kannada")]
        "kn" => (Language::Kannada, "kn", "\\p{Kannada}"),
        // Kurdish: Latin (Kurmanji) + Arabic (Sorani / Southern Kurdish)
        #[cfg(feature = "kurdish")]
        "ku" => (Language::Kurdish, "ku", "\\p{L}"),
        // Ganda / Luganda: Latin script only
        #[cfg(feature = "ganda")]
        "lg" => (Language::Ganda, "lg", "\\p{Latin}"),
        #[cfg(feature = "lao")]
        "lo" => (Language::Lao, "lo", "\\p{Lao}"),
        #[cfg(feature = "malayalam")]
        "ml" => (Language::Malayalam, "ml", "\\p{Malayalam}"),
        #[cfg(feature = "uzbek")]
        "uz" => (Language::Uzbek, "uz", "\\p{L}"),
        other => panic!("unsupported or disabled language code: {other}"),
    }
}

fn main() {
    let mut args = std::env::args().skip(1);
    let mode = args
        .next()
        .expect("mode required: testdata | model | merge | unique | mostcommon");
    let code = args.next().expect("language code required");
    let input_file = PathBuf::from(args.next().expect("input file required"));
    let repo_root = PathBuf::from(args.next().unwrap_or_else(|| {
        std::env::current_dir().unwrap().to_string_lossy().to_string()
    }));
    // Only used by "merge": how often a previously unseen ngram must occur in the
    // new corpus before it is added to the existing model.
    let min_new_ngram_count: u32 = args.next().and_then(|it| it.parse().ok()).unwrap_or(5);

    let (language, dir_code, char_class) = lang_meta(&code);
    let lang_dir = repo_root.join("language-models").join(dir_code);
    let models_dir = lang_dir.join("models");
    let testdata_dir = lang_dir.join("testdata");
    std::fs::create_dir_all(&models_dir).unwrap();
    std::fs::create_dir_all(&testdata_dir).unwrap();

    match mode.as_str() {
        "testdata" => {
            println!("Writing test data files for {code} to {}", testdata_dir.display());
            TestDataFilesWriter::create_and_write_test_data_files(
                input_file.as_path(),
                testdata_dir.as_path(),
                char_class,
                1000,
            )
            .expect("failed writing test data");
        }
        "model" => {
            println!("Writing language model file for {code} to {}", models_dir.display());
            LanguageModelFilesWriter::create_and_write_language_model_files(
                input_file.as_path(),
                models_dir.as_path(),
                language,
                char_class,
            )
            .expect("failed writing language model files");
        }
        "merge" => {
            println!(
                "Merging new corpus into existing language model for {code} in {}",
                models_dir.display()
            );
            LanguageModelFilesWriter::merge_and_write_language_model_files(
                input_file.as_path(),
                models_dir.as_path(),
                language,
                char_class,
                min_new_ngram_count,
            )
            .expect("failed merging language model files");
        }
        "unique" => {
            let staging = std::env::temp_dir().join("lingua_unique_staging");
            if staging.exists() {
                std::fs::remove_dir_all(&staging).unwrap();
            }
            std::fs::create_dir_all(&staging).unwrap();
            println!("Writing unique ngram files to staging dir {}", staging.display());
            UniqueNgramsWriter::create_and_write_unique_ngram_files(staging.as_path())
                .expect("failed writing unique ngrams");

            let src = staging.join(language.iso_code_639_1().to_string()).join("unique-ngrams.fst");
            if src.exists() {
                std::fs::copy(&src, models_dir.join("unique-ngrams.fst")).unwrap();
                println!("Copied unique-ngrams.fst");
            } else {
                eprintln!("No unique ngrams produced for {code}");
            }
        }
        "mostcommon" => {
            let staging = std::env::temp_dir().join("lingua_mostcommon_staging");
            if staging.exists() {
                std::fs::remove_dir_all(&staging).unwrap();
            }
            std::fs::create_dir_all(&staging).unwrap();
            let languages = std::collections::HashSet::from([language]);
            println!("Writing most-common ngram files for {code}");
            MostCommonNgramsWriter::create_and_write_most_common_ngram_files(
                staging.as_path(),
                &languages,
                25,
            )
            .expect("failed writing most-common ngrams");
            let src = staging.join(language.iso_code_639_1().to_string()).join("mostcommon-ngrams.fst");
            if src.exists() {
                std::fs::copy(&src, models_dir.join("mostcommon-ngrams.fst")).unwrap();
                println!("Copied mostcommon-ngrams.fst");
            } else {
                eprintln!("No most-common ngrams produced for {code}");
            }
        }
        other => panic!("unknown mode: {other}"),
    }
    println!("Done.");
}
