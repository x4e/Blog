---
title: "What are InvokeDynamics and how do they work?"
author: x4e
keywords: [jvm,bytecode]
description: "An explanation of what the invokedynamic instruction is and how it works"
date: 27th April 2021
unlisted: true
---

In the Java Virtual Machine version 7 the `CONSTANT_InvokeDynamic` constant pool type was introduced, followed it's cousin the `CONSTANT_Dynamic` type in version 11.
These two types are very complicated to understand and there seems to be a lack of sufficient resources to teach their purpose, functionality and use, so that is what I will attempt to do.

# Method Handles

A method handle is an instance of the Java runtime abstract class `java.lang.invoke.MethodHandle`.
This abstract class allows the invocation of a MethodHandle similar to that of a class like `java.util.function.Consumer` -- you have methods such as `invoke` which is able to take arguments and give back a return value.

In practice, method handles usually refer to something like a method, field, or constructor and when invoked will peform operations such as calling the method, setting/getting the field, or allocating an object and calling it's constructor.
Method handles can also be a transformation of another method handle; one possible transformation might be to spread a given array argument into individual arguments in the underlying method handle -- this transformation is actually provided by `MethodHandle.asSpreader`[^1].

[^1]: <https://docs.oracle.com/en/java/javase/15/docs/api/java.base/java/lang/invoke/MethodHandle.html#asSpreader(int,java.lang.Class,int)>

Method handles also store a "type" which describes the parameters it should be expecting and the return type you should be expecting.

## Signature Polymorphic Methods

The signature of `Object.equals` is `(Ljava/lang/Object;)Z` -- the method takes an Object and returns a boolean.
This is baked into the method and it's caller (an invokevirtual operation).

The power of a polymorphic signature is that there are no baked in argument types - you can pass any arguments you like and receive any return type you like.

This is somewhat present already in Java - due to it's inheritance model any reference type can be expressed as a `java.lang.Object`, so surely you could create a method like this, which can receive any type and number of arguments and any type of return value:
```Java
final native Object myMethod(Object... args);
```
Well, not quite.
While this will allow every **reference** type, there are plenty of types that cannot be expressed as an Object -- think primitives and void.
This definition would not allow you to pass an integer (at least not without boxing), and would not allow you to return `void`.

### How do we define a signature polymorphic method?

[JVMS 2.9.3](https://docs.oracle.com/javase/specs/jvms/se15/html/jvms-2.html#jvms-2.9.3) defines a method as being signature polymorphic if:

* It is declared in the java.lang.invoke.MethodHandle class or the java.lang.invoke.VarHandle class.
* It has a single formal parameter of type Object[].
* It has the ACC_VARARGS and ACC_NATIVE flags set.

(Note: No requirement on the return type)

This means a polymorphic function could be declared like so (in the right class):
```Java
final native Object myMethod(Object... args);
```
The method's signature is identical to that of our Object polymorphic method, except this method has an annotation that tells the JVM to treat this method with a polymorphic signature.

**Side Note:** If you look at the source of the signature polymorphic `invokeExact` method you will notice it has a special annotation:
```Java
public final native @PolymorphicSignature Object invokeExact(Object... args) throws Throwable;
```
When first writing this post I assumed that the way the JVM detects methods is with this annotation.
Weirdly it is completely unrelated, and I guess just some source level way of highlighting it?
Even that doesn't make much sense though since it is set to be retained at runtime.

### How do we use a signature polymorphic method?

The best way to describe this is to show how they are compiled.
I will use `MethodHandle.invokeExact` as an example of a signature polymorphic method, and a custom method to show a regular varargs invocation.
```Java
public class Main {
	public static void main(String[] args) throws Throwable {
		var arr = new ArrayList();
		// we dont actually care what method handle is, 
		// we just want to see the outputted bytecode
		var mh = (MethodHandle) null;
		int out = (int) mh.invokeExact(arr);
		Integer boxed = (Integer) myPolymorphicMethod(arr);
	}
	
	private static Object myPolymorphicMethod(Object... args) {
		return null;
	}
}
```

This is compiled to:
```Java
	public static void main(java.lang.String[]) throws java.lang.Throwable;
		descriptor: ([Ljava/lang/String;)V
		flags: (0x0009) ACC_PUBLIC, ACC_STATIC

		Code:
			stack=4, locals=5, args_size=1
				start local 0 // java.lang.String[] args
				 0: new           #7                  // class java/util/ArrayList
				 3: dup
				 4: invokespecial #9                  // Method java/util/ArrayList."<init>":()V
				 7: astore_1
				start local 1 // java.util.ArrayList arr
				 8: aconst_null
				 9: checkcast     #10                 // class java/lang/invoke/MethodHandle
				12: astore_2
				start local 2 // java.lang.invoke.MethodHandle mh
				13: aload_2
				14: aload_1
				15: invokevirtual #12                 // Method java/lang/invoke/MethodHandle.invokeExact:(Ljava/util/ArrayList;)I
				18: istore_3
				start local 3 // int out
				19: iconst_1
				20: anewarray     #2                  // class java/lang/Object
				23: dup
				24: iconst_0
				25: aload_1
				26: aastore
				27: invokestatic  #16                 // Method myPolymorphicMethod:([Ljava/lang/Object;)Ljava/lang/Object;
				30: checkcast     #22                 // class java/lang/Integer
				33: astore        4
				start local 4 // java.lang.Integer boxed
				35: return
				end local 4 // java.lang.Integer boxed
				end local 3 // int out
				end local 2 // java.lang.invoke.MethodHandle mh
				end local 1 // java.util.ArrayList arr
				end local 0 // java.lang.String[] args
```

When we call a varargs method such as `myPolymorphicMethod`, the methods descriptor is not *actually* polymorphic -- it only takes a single argument which is an Object array.
The compiler simply boxes any arguments into the array which lets the method *effectively* take a variable number of arguments.
Obviously this has an overhead.
You can see by the generated bytecode this is avoided by the `PolymorphicSignature` method - the caller specifies whichever descriptor it wants and the JVM will allow it.

Another benefit of this approach is the support for primitives: as you can see the `PolymorphicSignature` method is able to have primitives specified in it's descriptor.
When interacting with `myPolymorphicMethod` any primitives must be boxed in order to be passed around as references.
These dynamic descriptors even extend to `void`, allowing polymorphic descriptor methods to not return a value - something that would otherwise not be possible.

The value with these methods is obvious: the ability to invoke methods with any arguments, without overhead of primitive boxing/unboxing or array creation.

## Using Method Handles


