#!/usr/bin/env -S perl -w

use Digest::SHA ();

# getopt
if (@ARGV and $ARGV[0] eq '--') {
	shift;
}

my $file = shift;

if (!defined($file)) {
	if (-t STDIN) {
		die <<HAZ_TTY;
E: It appears that I am eating up your terminal!!!
E: To hash stdin, you must explicity pass \`-' as the file.
usage: $0 [--] FILE
HAZ_TTY
	}
	$file = '-';
}

if ($file eq '-') {
	my $proc = doit(\*STDIN);
	warn "Read $proc octet@{['s' x ($proc != 1)]}\n";
	exit 0;
} else {
	my @stat = stat($file) or die "$0: stat $file: $!\n";
	my $size = $stat[7];
	open my $File, '<', $file or die "$0: open $file: $!\n";
	binmode($File);
	my $proc = doit($File);
	close $File or die "$0: close $file: $!\n";
	warn "Read $proc of $size octet@{['s' x ($size != 1)]}\n";
	exit ($proc == $size ? 0 : 1);
}

sub doit {
	my $FILE = shift;
	my %dig = (
		SHA => Digest::SHA->new(1),
		384 => Digest::SHA->new(384),
	);
	local ($/, $!);
	my $proc = 0;
	$/ = \(1 << 13);
	while (<$FILE>) {
		foreach my $dig (values %dig) {
			$dig->add($_);
		}
		$proc += length;
	}
	print "sha384-", $dig{384}->b64digest(), "\n";
	print "?v=", $dig{SHA}->b64digest(), "\n";
	STDOUT->flush();
	return $proc;
}
