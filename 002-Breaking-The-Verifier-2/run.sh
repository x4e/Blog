cargo build
java -jar ../asmtools.jar jasm Illegal.jasm
javac Test.java
java -Djava.library.path=./target/debug/ Test
