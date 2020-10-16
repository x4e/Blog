cargo build
java -jar ../asmtools.jar jasm Illegal.jasm
javac Test.java
java -Xlog:verification -Djava.library.path=./target/debug/ Test
