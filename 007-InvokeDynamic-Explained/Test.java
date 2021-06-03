import java.lang.reflect.*;
import java.lang.invoke.*;
import java.util.*;

public class Test {
	public static void main(String[] args) throws Throwable {
		var method = System.class.getDeclaredMethod("exit", int.class);
		method.invoke(null, 2);
		
		MethodHandles.Lookup lookup = MethodHandles.lookup();
		var mh = lookup.findStatic(System.class, "exit", MethodType.methodType(void.class, int.class));
		mh.invokeExact(2);
	}
}
