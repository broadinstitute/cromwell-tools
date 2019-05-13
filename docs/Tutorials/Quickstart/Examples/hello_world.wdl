import "helloworld.wdl" as hw

workflow HelloWorld {
  String python_environment
  
  meta {
    description: "Hello World workflow."
  }

  call hw.HWTask {
    input:
      hello_input = "Hello World",
      python_environment = python_environment
  }
}
