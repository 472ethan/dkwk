dev:
	bundle exec ruby HTTPd.rb

www:
	bundle exec ruby HTTPd.rb -p 9000 engine-www

init:
	bundle config set path vendor/bundle
	bundle install

.PHONY: init dev www
