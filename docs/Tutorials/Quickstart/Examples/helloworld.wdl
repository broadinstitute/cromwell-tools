task HWTask {

  String hello_input
  String version = "hello_world_v1.0.0"
  String python_environment


  command {
    echo ${hello_input}

    python -u<<CODE

    chars = """Hello World!"""
    print(chars)

    import sys
    print(sys.version)

    CODE
  }

  runtime {
    docker: (if python_environment == "python3" then "python:3.6" else "python:2.7") + "-slim"
  }
}
