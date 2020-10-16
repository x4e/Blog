use std::os::raw::{c_void, c_int, c_char, c_uchar};
use std::ptr::null_mut;
use rs_jvm_bindings::jni::{JavaVM, JNI_VERSION_1_6, JNIEnv, jclass, jmethodID, jstring, jvalue};
use std::ffi::CString;
use detour::RawDetour;
use std::borrow::Borrow;
use libc::{dlsym, dlopen};

fn to_c_str<T: Into<Vec<u8>>>(str: T) -> *const c_char {
	let cstr = CString::new(str).unwrap();
	cstr.into_raw()
}

unsafe fn from_c_str(str: *const c_char) -> String {
	assert!(!str.is_null());
	let cstr = CString::from_raw(str as *mut c_char);
	cstr.into_string().unwrap()
}

const RTLD_LAZY: c_int = 0x00001;

type VerifyMethodType = extern fn(env: *mut c_void, class: *mut c_void, buffer: *mut c_char, len: c_int, major_version: c_int) -> c_uchar;

pub unsafe extern "C" fn dont_verify_lol(_env: *mut c_void, _class: *mut c_void, _buffer: *mut c_char, _len: c_int, _major_version: c_int) -> c_uchar {
	return 1;
}

#[no_mangle]
pub unsafe extern "system" fn JNI_OnLoad(_vm: *mut JavaVM, _reserved: &mut c_void) -> c_int {
	JNI_VERSION_1_6 as i32
}

static mut PATH: Option<String> = None;
static mut HOOK: Option<RawDetour> = None;

#[no_mangle]
pub unsafe extern "system" fn Java_Test_run(env: *mut JNIEnv, _class: jclass) {
	let system: jclass = (**env).FindClass.unwrap()(env, to_c_str("java/lang/System"));
	let method: jmethodID = (**env).GetStaticMethodID.unwrap()(env, system, to_c_str("getProperty"), to_c_str("(Ljava/lang/String;)Ljava/lang/String;"));
	let name: jstring = (**env).NewStringUTF.unwrap()(env, to_c_str("sun.boot.library.path"));
	let args: Vec<jvalue> = vec![jvalue { l: name }; 1];
	let out: jstring = (**env).CallStaticObjectMethodA.unwrap()(env, system, method, args.as_ptr());
	assert!(!out.is_null());
	PATH = Some(from_c_str((**env).GetStringUTFChars.unwrap()(env, out, null_mut())));
	
	let dl: *mut c_void = dlopen(to_c_str(format!("{}/libverify.so", PATH.clone().unwrap())), RTLD_LAZY);
	
	let symbol_ptr: *mut c_void = dlsym(dl, to_c_str("VerifyClassForMajorVersion"));
	
	let hook = RawDetour::new(symbol_ptr as *const (), dont_verify_lol as *const ())
		.expect("target or source is not usable for detouring");
	hook.enable().expect("Couldn't enable hook");
	HOOK = Some(hook);
}


#[no_mangle]
pub unsafe extern "system" fn Java_Test_test(_env: *mut JNIEnv, _class: jclass) {
	// test hook is active
	let hook = HOOK.borrow().as_ref().unwrap();
	assert!(hook.is_enabled());
	
	let dl: *mut c_void = dlopen(to_c_str(format!("{}/libverify.so", PATH.clone().unwrap())), RTLD_LAZY);
	
	let symbol_ptr: *mut c_void = dlsym(dl, to_c_str("VerifyClassForMajorVersion"));
	let symbol: VerifyMethodType = std::mem::transmute(symbol_ptr);
	symbol(null_mut(), null_mut(), null_mut(), 0, 0);
}



