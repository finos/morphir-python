fn main() {
    let rustc = std::env::var("RUSTC").expect("Cargo identifies its compiler");
    let output = std::process::Command::new(rustc)
        .arg("-vV")
        .output()
        .expect("read compiler identity");
    assert!(output.status.success());
    let version = String::from_utf8(output.stdout)
        .expect("compiler identity is UTF-8")
        .replace('\n', " | ");
    println!("cargo:rustc-env=QUALIFICATION_RUSTC={version}");
    for variable in ["PROFILE", "OPT_LEVEL", "DEBUG"] {
        let value = std::env::var(variable).expect("Cargo identifies its build settings");
        println!("cargo:rustc-env=QUALIFICATION_{variable}={value}");
    }
    println!("cargo:rerun-if-changed=build.rs");
}
