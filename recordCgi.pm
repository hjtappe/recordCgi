#!/usr/bin/perl -w

package RCGI;
use strict;

BEGIN{
	use Exporter ();
	use Config::Simple;
	use File::Basename;
	use vars       qw($VERSION @ISA @EXPORT @EXPORT_OK %EXPORT_TAGS);
	$VERSION=0.1;
	@ISA         = qw(Exporter);
	%EXPORT_TAGS = ( );     # eg: TAG => [ qw!name1 name2! ],
	@EXPORT_OK   = qw();
	@EXPORT= qw(&RCGI_printFree &mp3Val &w64Val &wavVal &printHeader &printTrailer &scriptName &archivDir &spoolDir &transcoder);

	sub new()
	{
		my $class = shift;
		my $cfg = new Config::Simple(syntax=>'simple');
		my $self = {
			_cfg => \$cfg,
		};

		$cfg->autosave(1);
		$cfg->read(&configFile);

		bless $self, $class;
		return $self;	
	}

	sub param()
	{
		my $self = shift;
		my $keyName = shift;
		my $value = shift;
		my $cfg = ${$self->{_cfg}};

		if (defined($value)) {
			return $cfg->param($keyName, $value);
		} else {
			return $cfg->param($keyName);
		}
	}
}
use vars @EXPORT_OK;
1;

# Space calculation multiplicators. Bytes per second.
my $mp3ToTime = 24469;
my $w64ToTime = 392097;
my $wavToTime = 180119;

my $scriptName;
if (defined($ENV{SCRIPT_NAME})) {
	$scriptName = $ENV{SCRIPT_NAME};
} else {
	$scriptName = basename($0);
}

sub scriptName()
{
	return $scriptName;
}

sub thisDir()
{
	my $thisDir = `dirname $0`;
	$thisDir =~ s/\s*$//g;
	return $thisDir;
}

sub archivDir()
{
	return &thisDir().'/Archiv';
}

sub spoolDir()
{
	return &thisDir().'/spool';
}

sub configFile()
{
	return &archivDir()."/.recordCgi.conf";
}

sub transcoder()
{
	return &thisDir()."/moveTranscode.sh 2>&1";
}

sub mp3Val()
{
	return $mp3ToTime;
}

sub w64Val()
{
	return $w64ToTime;
}

sub wavVal()
{
	return $wavToTime;
}

sub RCGI_printFree()
{
	# Disk Free in kB.
	my $df = qx(df -k . | sed '2{s,  *, ,g;q};d' | cut -d ' ' -f 4);
	# We need space for:
	# - the initial recording
	# - the wav.
	# When encoding the MP3, the initial recording will habe been removed, so we
	# can leave the MP3 size out here; no extra space needed.
	# When building the ISO image (MP3 size), the W64 still is bigger
	# (about twice the WAV size), so ignore it here. The storage peak is the
	# time of transcoding the W64 to WAV.
	# Free record time in seconds: Divide the bytes...
	my $recordTime = ($df * 1024) / ($w64ToTime + $wavToTime);
	print "<P>Verf&uuml;gbarer Speicherplatz: ";
	if (int($recordTime / 60) < 120) {
		print "<FONT COLOR=\"#FF0000\">";
	}
	print int($df / 1024).",",
		(($df % 1024) % 100)."MB";
#	print "(min. ",
#		int($recordTime / 60).":";
#	if (($recordTime % 60) < 10) {
#		print "0".($recordTime % 60);
#	} else {
#		print ($recordTime % 60);
#	}
#	print " neue CD-Brennauftr&auml;ge)\n";
	if (int($recordTime / 60) < 120) {
		print "</FONT>";
	}
	print "</P>\n";
	if (int($recordTime / 60) < 120) {
		print "<P><BLINK><FONT COLOR=\"#FF0000\"><B>KNAPPER SPEICHERPLATZ!</B></FONT></BLINK></P>";
	}
}

sub printHeader()
{
	my $title = shift;
	print << "EOT";
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="de" lang="de">

<head>
		<meta http-equiv="content-type" content="text/html; charset=utf-8" />
		<meta http-equiv="expires" content="0" />

		<meta name="language" content="de" />
		<title>$title</title>
	<script type="text/javascript">
	var doScroll = 0;
	function scrollDown() {
		if (doScroll != 0) {
			window.scrollBy(0, 500);
			setTimeout("scrollDown()", 1000);
		} else {
			// Jump to the end
			window.scrollBy(0, 500);
		}
	}
	function startScroll() {
		doScroll = 1;
		scrollDown();
	}
	function stopScroll() {
		doScroll = 0;
	}
	</script>
	</head>
	<body onkeydown="stopScroll();">
EOT
}

sub printTrailer()
{
	print << 'EOT';
	<script type="text/javascript">
		<!--
		stopScroll();
		-->
	</script>
	</BODY>
</HTML>
EOT
}

