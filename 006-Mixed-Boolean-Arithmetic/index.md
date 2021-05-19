---
title: "Mixed Boolean Arithmetic Obfuscation"
author: x4e
keywords: [jvm,bytecode,obfuscation]
description: "Obfuscating mathematical operations with MBA"
date: 29th March 2021
---

Mathematical operations are central to modern computers, with every program making extensive use of them.
Algorithms for purposes such as licensing, encryption and hashing make extensive use of arithmetic operations and by nature have very high security requirement.
The ability to obfuscate the operations behind such algorithms can be very useful.

## Boolean Arithmetic

Boolean arithmetic is the basis of all computers.
It operates on binary numbers using the basic logical instructions such as AND, OR, and NOT.
These are typically implemented as simple combinations of NAND gates -- every logical operation can be implemented in only NAND gates.

Boolean operations are typically compounds of others.
The most basic example is a NAND gate which is simply a combination of an AND and a NOT.
On a more complex level, every single logic gate is usually implemented as a combination of NAND gates.
With a couple of NAND gates you can simulate every other logical operation.

The ability to combine boolean operations to simulate others allows options for obfuscation.
A simple recognisable operation can be swapped for a combination of other operations whose purpose may not be easily understood.

There are many substitution rules that can be used to swap out complex boolean expressions for simplified ones.
De Morgan's laws are an example of this.
They are as follows:
$$ \lnot (\lnot x \land \lnot y) \equiv x \lor y $$
$$ \lnot (\lnot x \lor \lnot y) \equiv x \land y $$

While these rules can be used to simplify expressions, they can also be used for the opposite purpose: to obfuscate an expression.
By simply swapping them around we get another perspective:
$$ x \lor y \equiv \lnot (\lnot x \land \lnot y) $$

We can very easily use this substitution to obscure code, however it is not particularly good -- it is very repetitive and patterns emerge very clearly.

To increase the diversity of the substitution, we can create our own and mix them together.
Let's consider the purpose of an XOR operation (operating on a single bit). An XOR operation will return true if the two inputs are not equal to each other.
$$ x \oplus y \equiv x \not\equiv y $$

Since in this model there are only two possible states of both x and y (0 and 1) we can expand this into either x being 1 and y being 0, or x being 0 and y being 1:
$$ x \oplus y \equiv (x \land \lnot y) \lor (\lnot x \land y) $$

This has now given us a very simple XOR substitution where the XOR is only on one bit (for example between booleans).

## Integer Arithmetic

Integers aren't something a circuit can traditionally deal with, but by combining logical operations to deal with signs and carrying it is possible to support them.

One traditional integer circuit is a full adder, this is a circuit that can take two binary numbers and add them together.
To demonstrate the ability to implement integer operations at a boolean level, I wrote this software emulator of a 32bit full adder using only boolean operations:
```Java
public class Adder {
	// Number of bits in an int, excluding sign
	private static final int BITS = 31;
	// A mask for each bit except the most significant (the sign)
	private static final int MSB_MASK = 
		Integer.parseInt("01111111111111111111111111111111", 2);
	// A mask for the least significant bit
	private static final int LSB_MASK = 
		Integer.parseInt("00000000000000000000000000000001", 2);
	
	private int carry;
	public final int result;
	
	public Adder(int x, int y) {
		int current = 0;
		for (int i = 0; i < BITS; i++) {
			// Add the least significant bits together
			int tmp = addBits(x & LSB_MASK, y & LSB_MASK);
			// Remove least significant bits
			x = x >> 1;
			y = y >> 1;
			
			// Add to most significant bit of result
			tmp = tmp << BITS;
			current = current | tmp;
			// Move it right
			current = current >> 1;
			// Don't allow the shift to change the sign
			current &= MSB_MASK; 
		}
		this.result = current;
	}
	
	// Add together the least significant bits of two ints
	// Respects and updates the carry flag
	private int addBits(int x, int y) {
		int xor = x ^ y;
		int result = xor ^ carry;
		carry = (x & y) | (xor & carry);
		return result;
	}
	
	public static int add(int x, int y) {
		return new Adder(x, y).result;
	}
	
	public static void main(String[] args) {
		int i1 = Integer.parseInt(args[0]);
		int i2 = Integer.parseInt(args[1]);
		int sum = add(i1, i2);
		String f = "%d + %d = %d";
		System.out.println(f.formatted(i1, i2, sum));
	}
}
```
This is obviously very inefficient due to being implemented in software, and also it is missing some optimisations used by modern computers, for example, calculating the carries all at once and then adding the bits in parallel.

While substituting an addition with a software level addition emulation would be relatively costly, there are much simpler integer substitutions that we can perform with the help of our boolean operators.

Of course the most obvious substitution might be:
$$ x + y \equiv y + x $$

This is not very obscure however. 
What we can do is emulate two's complement maths to obscure this addition. 
On a hardware level there is normally no implementation of a subtraction circuit, this would be very complicated, so instead we rely on another quite obvious substitution -- we rely on the double negative:
$$ x - y \equiv x + -y $$

In practice what this means is that, in a two's complement system, a computer can store the negative of a number $x$ as:
$$ -x \equiv \lnot x + 1 $$
$$ -0010 \equiv 1101 + 1 \equiv 1110 $$

The bit inversion also conveniently inverts the sign (the left most bit).

Now if we perform a simple addition between the two complement number's $0010$ ($2$) and $1110$ ($-2$) we get $0000$ ($0$).
Note that this requires us to ignore the overflow.
```
       |- overflow
       V
carry: 11100
        0010
     +  1110
     =  0000
```

This can be written in the form of a substitution as:
$$ x - y \equiv x + (\lnot y + 1) $$

Which can also be rewritten as:
$$ x + y \equiv x - (\lnot y - 1) $$

Unlike the simple $x + y \equiv y + x$ this substitution is much more complicated to understand and requires knowledge of both boolean integer representation (two's complement), boolean operations ($\lnot$), and integer operations (subtraction).

## Application

In the above code we came up with an effective substitution for a very common integer operation (subtraction) and also applied it to another (addition).
Unlike naive substitutions that may substitute within the same class of expression, our substitution mixes both integer and boolean operations, forcing the reader to evaluate many different styles of mathematics to understand the code's purpose.
One way the effectiveness of these substitutions can also be improved is by recursively substituting within previous substitutions.

As noted at the start of this post, these substitution methods would be very useful within code obfuscation, especially when cryptography is involved.
In my obfuscator, [Binscure](https://binclub.dev/binscure), we recursively apply lots of mixed substitutions to obscure the original operations -- here is an example of the obfuscated equivalent of the full adder I wrote above:
```Java
// Decompiled with: CFR 0.151
// Class Version: 15
public class Adder {
    public static int BITS = 31;
    public static int LSB_MASK;
    public static int MSB_MASK;
    public int carry;
    public int result;

    public static int add(int n, int n2) {
        return new Adder((int)n, (int)n2).result;
    }

    public int addBits(int n, int n2) {
        int n3;
        int n4 = n;
        int n5 = n2;
        int n6 = (n4 | ~n5) - ~n5 - n4 - 1;
        int n7 = (n5 & ~n6) * 2 - (n5 ^ n6);
        int n8 = (n7 ^ 1) - (1 & ~n7) * 2;
        int n9 = ~n4 + 1;
        int n10 = (n9 | 0xFFFFFFFF) * 2 - ~n9;
        int n11 = n5 - (n10 & n5);
        int n12 = (n10 ^ n11) + (n10 & n11) * 2;
        int n13 = ~(n4 - 1);
        int n14 = (n13 | 0xFFFFFFFF) * 2 - ~n13;
        int n15 = n12 & ~n14 | n14 & ~n12;
        int n16 = ((n14 | n12) - n12) * 2;
        int n17 = (n15 ^ n16) - (n16 & ~n15) * 2;
        int n18 = n17 + (n8 & ~n17);
        int n19 = ((n18 & ~n17) - (n17 & ~n18)) * 2;
        int n20 = n17 + (n8 & ~n17);
        int n21 = (n17 | ~n8) - ~n8;
        int n22 = (n20 & ~n21) - (n21 & ~n20);
        int n23 = ((n19 | n22) - n22) * 2;
        int n24 = (n19 | n22) & ~(n19 & n22);
        int n25 = n3 = (n23 & ~n24) - (n24 & ~n23);
        int n26 = this.carry;
        int n27 = n25 + ~((n25 | ~n26) - ~n26) + 1;
        int n28 = (n27 + (n26 & ~n27)) * 2 + ~(n26 & ~n27 | n27 & ~n26) + 1;
        int n29 = ~(n25 - 1);
        int n30 = (n29 | 0xFFFFFFFF) * 2 - ~n29;
        int n31 = (n26 | n30) - n30;
        int n32 = (n30 | n31) * 2 - (n30 ^ n31);
        int n33 = ~(n25 - 1) - ~-1 - 1;
        int n34 = (n32 | n33) - n33 + ~(n33 - (n32 & n33)) + 1;
        int n35 = (n28 | ~n34) - ~n34;
        int n36 = ((n28 ^ n35) - (n35 & ~n28) * 2) * 2;
        int n37 = (n34 | n28) - n28;
        int n38 = n37 + ((n28 | n34) - n34 & ~n37);
        int n39 = (n36 | n38) - (n36 & n38) + ~(((n38 | n36) - n36) * 2) + 1;
        int n40 = n;
        int n41 = 1 - n40 - 1;
        int n42 = (-1 + (n41 & ~-1)) * 2;
        int n43 = n41 & ~-1 | 0xFFFFFFFF & ~n41;
        int n44 = (n42 & ~n43) * 2 - (n42 ^ n43);
        int n45 = n44 + (n2 & ~n44);
        int n46 = (n45 & ~n44) - (n44 & ~n45);
        int n47 = (n46 + (n44 & ~n46)) * 2 + ~((n44 | n46) & (~n46 | ~n44)) + 1;
        int n48 = 1 + ~n40;
        int n49 = (-1 + (n48 & ~-1)) * 2;
        int n50 = (n48 | 0xFFFFFFFF) & (~-1 | ~n48);
        int n51 = ~((n49 & ~n50) - (n50 & ~n49)) + 1;
        int n52 = -((n51 | 0xFFFFFFFF) + (n51 & 0xFFFFFFFF)) + -1;
        int n53 = (n47 ^ n52) - (n52 & ~n47) * 2;
        int n54 = (n53 & ~1) - (1 & ~n53);
        int n55 = (1 + (n54 & ~1)) * 2;
        int n56 = (n54 | 1) & ~(n54 & 1);
        int n57 = n3;
        int n58 = -n57 + -1;
        int n59 = (n58 | 1) * 2 - (n58 ^ 1);
        int n60 = (-1 + (n59 & ~-1)) * 2 + ~((n59 | 0xFFFFFFFF) - (n59 & 0xFFFFFFFF)) + 1;
        int n61 = n60 + (this.carry & ~n60);
        int n62 = (n61 & ~n60) - (n60 & ~n61);
        int n63 = n62 + (n60 & ~n62);
        int n64 = (n62 | ~n60) - ~n60;
        int n65 = (n63 | n64) * 2 - (n63 ^ n64);
        int n66 = 1 + ~n57;
        int n67 = -1 + (n66 & ~-1);
        int n68 = (0xFFFFFFFF | ~n66) - ~n66;
        int n69 = (n67 | n68) * 2 - (n67 ^ n68);
        int n70 = n69 + (n65 & ~n69);
        int n71 = -n65 + -1;
        int n72 = (n71 + (-n69 + -1 & ~n71) | ~n70) - ~n70;
        int n73 = (n69 | ~n65) - ~n65;
        int n74 = ((n69 & ~n73) * 2 - (n69 ^ n73)) * 2;
        int n75 = (n72 | n74) - n74;
        int n76 = (n74 | n72) - n72;
        int n77 = (n75 & ~n76) - (n76 & ~n75);
        int n78 = n77 - ~(((n55 & ~n56) - (n56 & ~n55) | n77) - n77) - 1;
        int n79 = (n78 | n77) - n77;
        int n80 = n77 - (n78 & n77);
        int n81 = (n79 & ~n80) * 2 - (n79 ^ n80);
        int n82 = n77 - (n81 & n77);
        int n83 = (n81 | n82) * 2 - (n81 ^ n82);
        int n84 = -n77 + -1;
        int n85 = n84 + (n81 & ~n84);
        int n86 = -n77 + -1;
        int n87 = (n85 & ~n86) - (n86 & ~n85);
        this.carry = (n87 + (n83 & ~n87)) * 2 + ~(n83 & ~n87 | n87 & ~n83) + 1;
        return n39;
    }

    public Adder(int n, int n2) {
        int n3 = 0;
        for (int i = 0; i < 31; ++i) {
            int n4 = n;
            int n5 = 1 - n4 - 1;
            int n6 = -1 + (n5 & ~-1);
            int n7 = (0xFFFFFFFF | ~n5) - ~n5;
            int n8 = (n6 | n7) * 2 - (n6 ^ n7);
            int n9 = LSB_MASK;
            int n10 = (n9 | ~n8) - ~n8;
            int n11 = (n9 & ~n10) * 2 - (n9 ^ n10);
            int n12 = n11 + (n8 & ~n11);
            int n13 = (n11 | ~n8) - ~n8;
            int n14 = (n12 | n13) * 2 - (n12 ^ n13);
            int n15 = 1 - n4 - 1;
            int n16 = (n15 | 0xFFFFFFFF) - (n15 & 0xFFFFFFFF) - ~(((0xFFFFFFFF | ~n15) - ~n15) * 2) - 1;
            int n17 = (n14 | ~n16) - ~n16;
            int n18 = (n14 & ~n17) - (n17 & ~n14);
            int n19 = n14 + (n16 & ~n14);
            int n20 = (n19 & ~n14) * 2 - (n19 ^ n14);
            int n21 = n2;
            int n22 = 1 - n21 - 1;
            int n23 = (-1 + (n22 & ~-1)) * 2;
            int n24 = n22 & ~-1 | 0xFFFFFFFF & ~n22;
            int n25 = (n23 & ~n24) * 2 - (n23 ^ n24);
            int n26 = n25 + (LSB_MASK & ~n25) + ~n25 + 1;
            int n27 = (n25 | n26) & ~(n25 & n26);
            int n28 = ((n26 | ~n25) - ~n25) * 2;
            int n29 = (n27 | n28) + (n27 & n28);
            int n30 = -n21 + -1;
            int n31 = (n30 | 1) + (n30 & 1);
            int n32 = --1 + -1;
            int n33 = ~((n31 & ~n32) * 2 - (n31 ^ n32) + ~1 + 1) + 1 - ~-1 - 1;
            int n34 = n33 + (n29 & ~n33);
            int n35 = (n33 | ~n29) - ~n29;
            int n36 = (n34 | n35) + (n34 & n35);
            int n37 = this.addBits(((n18 | n20) - n20) * 2 + ~((n18 | n20) & (~n20 | ~n18)) + 1, (n36 | 1) - (n36 & 1) - ~(((1 | ~n36) - ~n36) * 2) - 1);
            n >>= 1;
            n2 >>= 1;
            int n38 = n37 <<= 31;
            int n39 = n3;
            int n40 = -n38 + -1;
            int n41 = n40 + (n39 & ~n40);
            int n42 = -n38 + -1;
            int n43 = (n41 ^ n42) - (n42 & ~n41) * 2;
            int n44 = -n39 + -1;
            int n45 = (n43 | n44) + (n43 & n44);
            int n46 = ((n38 | n45) - n45) * 2;
            int n47 = (n38 | n45) & ~(n38 & n45);
            int n48 = (n46 ^ n47) - (n47 & ~n46) * 2;
            int n49 = (n48 - (1 & n48)) * 2;
            int n50 = (n48 | 1) - (n48 & 1);
            n3 = (n49 & ~n50) * 2 - (n49 ^ n50);
            int n51 = n3 >>= 1;
            int n52 = 1 + ~n51;
            int n53 = --1 + -1;
            int n54 = (n52 ^ n53) - (n53 & ~n52) * 2;
            int n55 = (n54 ^ 1) - (1 & ~n54) * 2;
            int n56 = MSB_MASK;
            int n57 = (n56 | ~n55) - ~n55;
            int n58 = (n56 & ~n57) - (n57 & ~n56);
            int n59 = (n58 + (n55 & ~n58)) * 2;
            int n60 = n55 & ~n58 | n58 & ~n55;
            int n61 = (n59 ^ n60) - (n60 & ~n59) * 2;
            int n62 = -n51 + -1;
            int n63 = (n62 ^ 1) + (n62 & 1) * 2;
            int n64 = -1 + (n63 & ~-1);
            int n65 = (0xFFFFFFFF | ~n63) - ~n63;
            int n66 = (n64 | n65) + (n64 & n65);
            int n67 = n66 + (n61 & ~n66);
            int n68 = (n67 & ~n66) * 2 - (n67 ^ n66);
            int n69 = n61 + (n66 & ~n61) + ~n61 + 1;
            int n70 = (n68 | n69) - (n68 & n69);
            int n71 = ((n69 | n68) - n68) * 2;
            n3 = (n70 ^ n71) - (n71 & ~n70) * 2;
        }
        this.result = n3;
    }

    static {
        MSB_MASK = Integer.parseInt("01111111111111111111111111111111", 2);
        LSB_MASK = Integer.parseInt("00000000000000000000000000000001", 2);
    }

    public static void main(String[] stringArray) {
        int n = Integer.parseInt(stringArray[0]);
        int n2 = Integer.parseInt(stringArray[1]);
        int n3 = Adder.add(n, n2);
        String string = "%d + %d = %d";
        System.out.println(string.formatted(n, n2, n3));
    }
}

```
In fact, this code will completely crash some decompilers like JetBrain's Fernflower:
```Java
java.lang.OutOfMemoryError: Java heap space
	at org.jetbrains.java.decompiler.util.FastSparseSetFactory$FastSparseSet.<init>(FastSparseSetFactory.java:84)
	at org.jetbrains.java.decompiler.util.FastSparseSetFactory$FastSparseSet.<init>(FastSparseSetFactory.java:69)
	at org.jetbrains.java.decompiler.util.FastSparseSetFactory.spawnEmptySet(FastSparseSetFactory.java:57)
	at org.jetbrains.java.decompiler.modules.decompiler.sforms.SSAUConstructorSparseEx.setCurrentVar(SSAUConstructorSparseEx.java:699)
	at org.jetbrains.java.decompiler.modules.decompiler.sforms.SSAUConstructorSparseEx.processExprent(SSAUConstructorSparseEx.java:363)
	at org.jetbrains.java.decompiler.modules.decompiler.sforms.SSAUConstructorSparseEx.processExprent(SSAUConstructorSparseEx.java:231)
	at org.jetbrains.java.decompiler.modules.decompiler.sforms.SSAUConstructorSparseEx.processExprent(SSAUConstructorSparseEx.java:231)
	at org.jetbrains.java.decompiler.modules.decompiler.sforms.SSAUConstructorSparseEx.processExprent(SSAUConstructorSparseEx.java:231)
	at org.jetbrains.java.decompiler.modules.decompiler.sforms.SSAUConstructorSparseEx.processExprent(SSAUConstructorSparseEx.java:231)
	...
```

If you are interested in learning about more mixed boolean substitutions I recommend reading Hacker's Delight by Henry S. Warren, Jr.
