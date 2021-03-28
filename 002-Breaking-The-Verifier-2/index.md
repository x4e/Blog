---
title: "Breaking The Verifier #2"
author: x4e
keywords: [jvm,verifier]
description: "Breaking the verifier for all OpenJDK 8+ JVMs by hooking shared library exports"
date: 17th October 2020
---

Breaking the verifier for all OpenJDK 8+ JVMs by hooking shared library exports.

Make sure you've read #1 before this, so you have a basic understanding of what the verifier is and why it's important.


## Some background

Before Java 6, classes were verified in two stages:

* First, the type-inferencing verifier did type emulations of methods in order to predict the types of any values used
* Secondly, the type-checking verifier verified that types were used accurately

A team working on the "Connected Limited Device Configuration" complained that this process, specifically the first stage, was slow and expensive to perform, particularly on embedded systems. They proposed the split verifier.

The split verifier has similar stages to the original verifier, except that the first stage is performed at compile time, and embedded into the class file's "StackMapTable" attributes by the compiler.
This shifts the cost to compile time, potentially speeding up runtime class loading.

The split verifier was initially intended to be shipped with Java 5 (Tiger release), but landed in Java 6, where the Java compiler had an optional experimental flag to generate the StackMapTable attributes, and the JVM would only use them if they were present.

In Java 7 the StackMapTables were made mandatory for any version 7 class files, and the compiler produced them by default.
However, to support older class files, the old verification method (now bundled externally in `verify.dll` or `libverify.so`) is used for any class files version 6 or less.	


## Breaking this

Let's take a look at the JVM code for loading the `verify` dynamic library that contains the split verifier

[verifier.cpp#L66](https://github.com/openjdk/jdk/blob/976acddeb5a8df1e868269787c023306aad3fe4a/src/hotspot/share/classfile/verifier.cpp#L66):
```{.cpp startFrom="66"}
// Access to external entry for VerifyClassForMajorVersion - old byte code verifier

extern "C" {
  typedef jboolean (*verify_byte_codes_fn_t)(JNIEnv *, jclass, char *, jint, jint);
}

static verify_byte_codes_fn_t volatile _verify_byte_codes_fn = NULL;

static verify_byte_codes_fn_t verify_byte_codes_fn() {

  if (_verify_byte_codes_fn != NULL)
    return _verify_byte_codes_fn;

  MutexLocker locker(Verify_lock);

  if (_verify_byte_codes_fn != NULL)
    return _verify_byte_codes_fn;

  // Load verify dll
  char buffer[JVM_MAXPATHLEN];
  char ebuf[1024];
  if (!os::dll_locate_lib(buffer, sizeof(buffer), Arguments::get_dll_dir(), "verify"))
    return NULL; // Caller will throw VerifyError

  void *lib_handle = os::dll_load(buffer, ebuf, sizeof(ebuf));
  if (lib_handle == NULL)
    return NULL; // Caller will throw VerifyError

  void *fn = os::dll_lookup(lib_handle, "VerifyClassForMajorVersion");
  if (fn == NULL)
    return NULL; // Caller will throw VerifyError

  return _verify_byte_codes_fn = CAST_TO_FN_PTR(verify_byte_codes_fn_t, fn);
}
```

Quite simply, the JVM loads the `verify` library, then searches for the `VerifyClassForMajorVersion` function within it.

How can we exploit this?

We can:

1. Get a handle to the same library
2. Find the same function
3. Hook said function

To implement this I will be using rust. Sources are included in [src/lib.rs](https://github.com/x4e/Blog/blob/master/002-Breaking-The-Verifier-2/src/lib.rs). 
I've only implemented this for Linux but feel free to extend it to other operating systems. Should only require `dlopen` and `dlsym` being replaced with alternatives.

First I need to find the folder where java will store its libraries. This is stored in the property `sun.boot.library.path`.
```rust
let system: jclass = (**env).FindClass.unwrap()(env, to_c_str("java/lang/System"));
let method: jmethodID = (**env).GetStaticMethodID.unwrap()(env, system, to_c_str("getProperty"), to_c_str("(Ljava/lang/String;)Ljava/lang/String;"));
let name: jstring = (**env).NewStringUTF.unwrap()(env, to_c_str("sun.boot.library.path"));
let args: Vec<jvalue> = vec![jvalue { l: name }; 1];
let out: jstring = (**env).CallStaticObjectMethodA.unwrap()(env, system, method, args.as_ptr());
assert!(!out.is_null());
PATH = Some(from_c_str((**env).GetStringUTFChars.unwrap()(env, out, null_mut())));
```

Now I can retrieve a handle to the `verify` DLL:
```rust
let dl: *mut c_void = dlopen(to_c_str(format!("{}/libverify.so", PATH.clone().unwrap())), RTLD_LAZY);
```

And then retrieve a pointer to the verify function:
```rust
let symbol_ptr: *mut c_void = dlsym(dl, to_c_str("VerifyClassForMajorVersion"));
```

Now I will use the `detour` crate to hook the method, this just modifies the function assembly to call my own function instead:
```rust
pub unsafe extern "C" fn dont_verify_lol(_env: *mut c_void, _class: *mut c_void, _buffer: *mut c_char, _len: c_int, _major_version: c_int) -> c_uchar {
	// 1 == class file is legal
	return 1;
}

let hook = RawDetour::new(symbol_ptr as *const (), dont_verify_lol as *const ())
	.expect("target or source is not usable for detouring");
hook.enable().expect("Couldn't enable hook");
HOOK = Some(hook);
```

And that's it... Now any class verified with the split verifier will instantly pass verification.

You can test this by running [run.sh](https://github.com/x4e/Blog/blob/master/002-Breaking-The-Verifier-2/run.sh).



## Edit 1

As it turns out, this can be used to bypass verification on up to **Java 7** class files. That's pretty big for obfuscators, as Java 7 still supports features like InvokeDynamic, and it is possible to convert Java 8 classes into Java 7.

It turns out that the JVM is able to failover to the old split verifier if a class file (with a version <=J7) fails the new verification

[verifier.cpp#L194](https://github.com/openjdk/jdk/blob/976acddeb5a8df1e868269787c023306aad3fe4a/src/hotspot/share/classfile/verifier.cpp#L194)
```{.cpp startFrom="194"}
    ClassVerifier split_verifier(klass, THREAD);
    split_verifier.verify_class(THREAD);
    exception_name = split_verifier.result();
	
    bool can_failover = !DumpSharedSpaces &&
      klass->major_version() < NOFAILOVER_MAJOR_VERSION;

    if (can_failover && !HAS_PENDING_EXCEPTION &&  // Split verifier doesn't set PENDING_EXCEPTION for failure
        (exception_name == vmSymbols::java_lang_VerifyError() ||
         exception_name == vmSymbols::java_lang_ClassFormatError())) {
      log_info(verification)("Fail over class verification to old verifier for: %s", klass->external_name());
      log_info(class, init)("Fail over class verification to old verifier for: %s", klass->external_name());
      message_buffer = NEW_RESOURCE_ARRAY(char, message_buffer_len);
      exception_message = message_buffer;
      exception_name = inference_verify(
        klass, message_buffer, message_buffer_len, THREAD);
    }
    if (exception_name != NULL) {
      exception_message = split_verifier.exception_message();
    }
```
