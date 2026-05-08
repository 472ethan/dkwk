#!/usr/bin/env ruby
# In crude imitation of "un.rb"

require "ipaddr"
require "socket"
require "optparse"
begin
  require "webrick"
rescue
  abort "E: You need \`webrick' to run #{$0}."
end

# Options!
options = {
  port:  8080,  # (tcp 8000 taken by engine)
  host:  IPAddr.new(Socket::INADDR_LOOPBACK, Socket::AF_INET).to_s,
  root:  "public_html",
}

OptionParser.new do |o|
  options[:name] = o.program_name
  o.banner = "Usage: #{o.program_name} [-h] [-o ADDR] [-p PORT] [root]"
  o.on("-h", "--help", "Print this help message") do
    puts o
    exit
  end
  o.on("-b", "-o", "--bind", "--host ADDR",
       "Bind address (default: #{options[:host]})"
  ) do |it|
    options[:host] = it
  end
  o.on("-p", "--port PORT", Integer,  # Type coersion!
       "Bind TCP port (default: #{options[:port]})"
  ) do |it|
    options[:port] = it
  end
end.parse!(ARGV).each do |v|
  if options[:once]
    abort "#{options[:name]}: too many arguments"
  end
  options[:root] = v
  options[:once] = true
end

p options

s = WEBrick::HTTPServer.new(
  Host: options[:host],
  Port: options[:port],
  DocumentRoot: options[:root],
  DirectoryIndex: ["index.html"],
)
((%w(TERM QUIT) |
  %w(HUP INT) * (STDIN.tty? ? 1 : 0)  # only likely from a terminal
 ) & Signal.list.keys).each do |sig|
  Signal.trap(sig, proc {
    warn "Caught SIG#{sig.upcase}; shutting down #{options[:name]}"
    s.shutdown
  })
end
s.start
