# Breaking The Verifier #1

Bypassing the OpenJDK8 and OpenJ9 verifier through an unsecured backdoor.

<!--more-->

## Some background

The JVM was originally designed with web usage in mind. 
The idea was that you could run Java Applications from your web browser, and while this was popular, chrome began to start the process of removing it in 2015.

Obviously, for people to be able to run arbitrary Java applications in your browser there needs to be a form of security protection.
The JVM has three main enforcers of security:

- Access Checker
    - Checks access flags for things like fields, classes and methods
    - Enforced at native level
- Verifier
  - Verifies that classes contain "legal" bytecode
  - Enforced at native level
- Security Manager
  - Is able to prohibit actions such as accessing the file system
  - Enforced at Java level
  - Inactive in a regular java instance
	
In this post I am going to be breaking all three of these mechanisms.

## Why does the JVM have a verifier?

Java is compiled into an intermediate bytecode, which must follow [a strict set of rules defined by oracle](https://docs.oracle.com/javase/specs/jvms/se15/html/).
By having a well defined specification of easy to understand bytecode, users are easily able to dissasemble bytecode before running it on their machines, so that they can make sure they only run code that they trust.
It also means checks can be made to ensure, for example, that a jump instruction doesnt jump to abritrary memory addresses, for example on the heap (allowing generating code at runtime), or inside another method).

## Breaking it

Me and [xDark](https://github.com/xxDark) where spending a bit of time recently looking into potential JVM security flaws, when he stumbled across an interesting piece of code (So of course full credit for this goes to him, I am just creating a writeup).

Take a look at the following code from [reflection.cpp#L455](https://github.com/openjdk/jdk/blob/jdk8-b120/hotspot/src/share/vm/runtime/reflection.cpp#L455):
```C++
bool Reflection::verify_class_access(Klass* current_class, Klass* new_class, bool classloader_only) {
  // Verify that current_class can access new_class.  If the classloader_only
  // flag is set, we automatically allow any accesses in which current_class
  // doesn't have a classloader.
  if ((current_class == NULL) ||
      (current_class == new_class) ||
      (new_class->is_public()) ||
      is_same_class_package(current_class, new_class)) {
    return true;
  }
  // New (1.4) reflection implementation. Allow all accesses from
  // sun/reflect/MagicAccessorImpl subclasses to succeed trivially.
  if (   JDK_Version::is_gte_jdk14x_version()
      && UseNewReflection
      && current_class->is_subclass_of(SystemDictionary::reflect_MagicAccessorImpl_klass())) {
    return true;
  }

  return can_relax_access_check_for(current_class, new_class, classloader_only);
}
```
This method is called each time a class links agains another class.
It returns true if the class has permission to access the other class.
The basic implementation checks that the class is public or in the same package.

However, in Java 4 the reflection API was added. Because reflection inherently allows Java code to bypass access controls, a backdoor was added in the form of the class `sun.reflect.MagicAccessorImpl`. 
Java classes that are necessary for facilitating the reflection API can simply extend this class to *magically* bypass any access controls. Of course, if any class could bypass access flags (without using the reflection API which is guarded by the Security Manager) this would be a security risk. 
The solution was to make MagicAccessorImpl package private, meaning only other sun.reflect classes can access it.

There's one problem with this though: If you try to load a class that extends the magic accessor it will call `verify_class_access` to check if you can indeed access the magic accessor (which of course we shouldnt be able to). This method will see that you extend magic accessor, and therefore allow you to extend magic accessor.

By now we have broken the first stage of JVM security, the access checker. By simply extending a specific class we can bypass all access restrictions.

Now we will use this to break the second two.


[verifier.cpp#L188](https://github.com/openjdk/jdk/blob/jdk8-b120/hotspot/src/share/vm/classfile/verifier.cpp#L188)
```C++
bool Verifier::is_eligible_for_verification(instanceKlassHandle klass, bool should_verify_class) {
  Symbol* name = klass->name();
  Klass* refl_magic_klass = SystemDictionary::reflect_MagicAccessorImpl_klass();

  bool is_reflect = refl_magic_klass != NULL && klass->is_subtype_of(refl_magic_klass);

  return (should_verify_for(klass->class_loader(), should_verify_class) &&
    // return if the class is a bootstrapping class
    // or defineClass specified not to verify by default (flags override passed arg)
    // We need to skip the following four for bootstraping
    name != vmSymbols::java_lang_Object() &&
    name != vmSymbols::java_lang_Class() &&
    name != vmSymbols::java_lang_String() &&
    name != vmSymbols::java_lang_Throwable() &&

    // Can not verify the bytecodes for shared classes because they have
    // already been rewritten to contain constant pool cache indices,
    // which the verifier can't understand.
    // Shared classes shouldn't have stackmaps either.
    !klass()->is_shared() &&

    // As of the fix for 4486457 we disable verification for all of the
    // dynamically-generated bytecodes associated with the 1.4
    // reflection implementation, not just those associated with
    // sun/reflect/SerializationConstructorAccessor.
    // NOTE: this is called too early in the bootstrapping process to be
    // guarded by Universe::is_gte_jdk14x_version()/UseNewReflection.
    // Also for lambda generated code, gte jdk8
    (!is_reflect || VerifyReflectionBytecodes));
}
```

This backdoor into the access checker didn't completely allow the reflection API to function correctly, there was a bug.

While there is a refenced bug code (`4486457`) it seems to be private. There is however [an interesing email chain related to it](http://mail.openjdk.java.net/pipermail/jigsaw-dev/2016-December/010645.html):

> No it isn't public. Basically when the code-generating reflection
> mechanism was introduced verification had to be bypassed because the
> generated code didn't obey the expected subclassing rules for protected
> access - hence MagicAccessor.

What this essentially means is that verification will be **completely** disabled for all subclasses of MagicAccessor.
I've written a test class Test.jasm to test this. The class can be decompiled to something like below:
```Java
public class Test extends sun.reflect.MagicAccessorImpl {
	public static void main(String[] args) {
		System.out.println("Hello, world!");
		
		try {
			throw "You should not be able to throw a string!";
		} catch (String exception) {
			System.out.println(exception);
		}
	}
}
```
Obviously this code is invalid! You should not be able to throw a string.

Now compile [Test.jasm](https://github.com/x4e/Blog/blob/master/001-Breaking-The-Verifier-1/Test.jasm) and run `java Test` making sure that you are using java version 8. As you can see we throw, catch and print the string.

The second layer of the JVM's security is broken: we can load and execute completely illegal classes.
With this power we can now also trivially break the third layer: we can simply overwrite the `java.lang.System.securityManager` field with `null` to disable the security manager. Since we are doing a direct field set instead of `System.setSecurityManager` the security manager itself has no option to prevent this. And since the access checker is giving us magic powers, we are not prevented by the JVM.

## Future JVMs
Sadly this was broken after Java 8 with the introduction of the module system. Magic Accessor was relocated into the `jvm.internal` package which is in a module protected from user classes.
