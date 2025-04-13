use std::time::{SystemTime, UNIX_EPOCH};
use std::fs::File;
use std::io::Write;
use std::env;
use std::path::Path;

fn main() {
    // 获取当前时间作为编译日期
    let now = SystemTime::now();
    let since_epoch = now.duration_since(UNIX_EPOCH).expect("Time error");
    let now_secs = since_epoch.as_secs();
    
    // 使用chrono格式化当前时间，转换为东8区时间(UTC+8)
    let datetime = chrono::DateTime::<chrono::Utc>::from_timestamp(now_secs as i64, 0)
        .unwrap()
        .with_timezone(&chrono::FixedOffset::east_opt(8 * 3600).unwrap())
        .format("%Y-%m-%d %H:%M:%S")
        .to_string();
    
    // 读取Cargo.toml中的版本号
    let version = env!("CARGO_PKG_VERSION");
    
    // 设置编译时环境变量
    println!("cargo:rustc-env=BUILD_DATE={}", datetime);
    
    // 创建版本信息文件
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("../../../version_info.txt");
    
    // 使用纯ASCII字符的版本信息
    let version_info = format!("{}-parallel (Built on {})", version, datetime);
    
    // 写入版本信息到文件
    let mut f = File::create(&dest_path).unwrap();
    f.write_all(version_info.as_bytes()).unwrap();
    
    // 创建一个备份版本文件在项目根目录
    let root_version_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("version_info.txt");
    let mut f2 = File::create(&root_version_path).unwrap();
    f2.write_all(version_info.as_bytes()).unwrap();
    
    println!("cargo:warning=Version info written to: {}", dest_path.display());
    println!("cargo:warning=Backup version info written to: {}", root_version_path.display());
    println!("cargo:warning=Using Beijing time (UTC+8): {}", datetime);
    
    // 强制每次构建时重新运行此脚本
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=src/lib.rs");
}
