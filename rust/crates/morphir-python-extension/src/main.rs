//! Standalone process entry point; the compiler never imports or executes Python.
use morphir_python_extension::serve;

fn main() {
    let mut arguments = std::env::args_os().skip(1);
    let argument = arguments.next();
    if arguments.next().is_some() {
        eprintln!("Usage: morphir-python-extension --stdio");
        std::process::exit(2);
    }
    match argument.as_deref() {
        Some(value) if value == "--stdio" => {
            if let Err(error) = serve(&mut std::io::stdin().lock(), &mut std::io::stdout().lock()) {
                eprintln!("morphir-python-extension: {error}");
                std::process::exit(1);
            }
        }
        Some(value) if value == "--help" => println!("Usage: morphir-python-extension --stdio"),
        _ => {
            eprintln!("Usage: morphir-python-extension --stdio");
            std::process::exit(2);
        }
    }
}
