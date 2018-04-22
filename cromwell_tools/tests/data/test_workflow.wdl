import "test_task.wdl" as test_task

workflow hello_world {
  call test_task.hello_world {}
  output {
    File response = hello_world.response
  }
}
