#!/usr/bin/env perl

use Getopt::Long;
use File::Basename;
use File::Copy;
use Fcntl;
my $usage = "usage: $0 [-O initsys] [-h]\n";
my $initsys;

GetOptions(
	'O=s' => \$initsys,
	'h' => \my $help)
	or die $usage;

if ($help) {
	print $usage;
	exit;
}

unless ($initsys) {
	if ($^O eq 'freebsd') {
		$initsys = 'freebsd';
	} elsif ($^O eq 'linux') {
		my $initlink = -l '/sbin/init' ? basename(readlink('/sbin/init')) : undef;
		if (!defined $initlink) {
			die "Your /sbin/init isn't a symlink? How quaint.\n";
		} elsif ($initlink eq 'openrc-init') {
			die "I haven't written an openrc script (yet), sorry.\n";
		} elsif ($initlink eq 'systemd') {
			die "Just no.\n";
		} else {
			die "I am not familiar with your /sbin/init: $initlink\n";
		}
	} else {
		die "I'm not ready to handle the majestic $^O, sorry\n";
	}
}

if ($initsys eq 'freebsd') {
	my $bits = 0755;
	if (my $umask = umask) {
		$bits &= ~$umask;
	}
	my ($source, $target) = qw(dkwk /usr/local/etc/rc.d/dkwk);
	print STDERR sprintf "+ install -m %04o %s %s\n",
		$bits, $source, $target;
	my $file;
	sysopen my $file, $target, O_WRONLY|O_CREAT|O_TRUNC, $bits
		or die qq[open $target ">": $!\n];
	binmode $file;
	copy $source, $file;
	close $file;
} else {
	die "BUG";
}
