task hello_world {

  command {
    echo "Hello, world!" > hello_world.txt
  }

  output {
    String response = read_string("hello_world.txt")
  }
}
