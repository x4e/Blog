public class Test {
	public static void main(String[] args) throws Throwable {
		System.loadLibrary("verify");
		System.loadLibrary("NoVerify");
		run();
		System.out.println("Done");
		System.out.println(Class.forName("Illegal"));
	}

	public static native void run();
	public static native void test();
}
