#!/usr/bin/env perl
# TODO:
# - Design and implement a structured Archive that provides an acceptable
#   overview for lots of recordings
# - Design and implement a search over these lots of recordings
# - Design and implement a batch remove (or define this to be done from the
#   command line)

use strict;
use warnings;
use CGI::Carp qw(fatalsToBrowser);
BEGIN {
	use CGI;
	use Encode qw/from_to/;
	my $cdtextMaxSize = 64;
	my $cgi = new CGI;
	my $archivDir = "Archiv";
	my $wavFilePrefix = "tm";
	my $cdDevice = "/dev/cdrw";
	my $configFile = "config.cgi";

	# add the path to the perl module to @INC.
	my $mydir = `dirname $0`;
	$mydir =~ s/\s*$//g;
	$mydir =~ s/\r?\n$//;
	push(@INC, $mydir);
	require recordCgi;
	my $scriptName = &RCGI::scriptName();

	if ( -f $configFile && -r $configFile) {
		open (CFG, "<".$configFile) || die "Error opening $configFile";
		while (<CFG>) {
			my $line = $_;
			$line =~ s/#.*$//;
			$line =~ s/\s*$//;
			if ($line =~ /^\s*cdDevice\s*=\s*(.+)$/i) {
				$cdDevice = $1;
				$cdDevice =~ s/^"(.*)"$/$1/;
			}
		}
		close (CFG);
	}

#	print "Content-type: text/plain\n\n";
	print "Content-type: text/html\n\n";
	if (! -d $archivDir) {
		mkdir $archivDir;
	}
	if ((! -d $archivDir) || (! -w $archivDir)) {
		print "<p>Error. Create directory '".$archivDir."' and give access for the www-data user.</p>\n";
		return;
	}

	&RCGI::printHeader("recordCGI: Liste der Aufnahmen");
	print << "EOT";
  <P ALIGN=RIGHT><A HREF="help.htm">Dokumentation</A></P>
  <P><A HREF="archiv.cgi">Zu den Aufnahmen</A><BR>
  <A HREF="$scriptName">Aktualisieren</A><BR>
  <A HREF="$scriptName?erase=ask">CD-RW l&ouml;schen</A><BR>
EOT

	if (defined($cgi->param("edit"))) {
		&edit_file(scalar $cgi->param("jobId"));
	} elsif (defined($cgi->param("cleanup"))) {
		&cleanup;
		&show_list;
	} elsif (defined($cgi->param("save"))) {
		&save_file(scalar $cgi->param("jobId"));
		&show_list;
	} elsif (defined($cgi->param("remove"))) {
		&remove(scalar $cgi->param("jobId"));
	} elsif (defined($cgi->param("reallyremove"))) {
		&reallyRemove(scalar $cgi->param("jobId"));
		&show_list;
	} elsif (defined($cgi->param("erase"))) {
		&erase();
	} elsif (defined($cgi->param("reallyerase"))) {
		&show_list;
		&reallyerase(scalar $cgi->param("blank"));
	} elsif (defined($cgi->param("burn"))) {
		&burn(scalar $cgi->param("jobId"));
	} elsif (defined($cgi->param("dontburn"))) {
		&dontburn;
		&show_list;
	} elsif (defined($cgi->param("reallyburn"))) {
		&show_list;
		&reallyburn(scalar $cgi->param("jobId"));
	} else {
		&show_list;
	}

	&RCGI::printTrailer;

sub remove()
{
	my $jobId = shift;
	my $filename = $archivDir."/".$jobId.".mp3";
	my $firstLine = 1;

	if (! -r $filename) {
		print "    <P>Unable to find file ".$filename."</P>\n";
	} else {
		&show_jobDate($jobId);
		&show_jobinfo($jobId);
		my $scriptName = &RCGI::scriptName();
		print << "EOT";
    <FORM METHOD="post" action="$scriptName">
    <P><input type=submit name=\"reallyremove\" value=\"Wirklich l&ouml;schen.\">
    <input type=submit name=\"dontremove\" value=\"Abbrechen.\">
EOT
		print "    <input type=\"hidden\" name=\"jobId\" value=\"".$jobId."\"></P>\n";
		print << "EOT";
	</FORM>
EOT
	}
}

sub reallyRemove()
{
	my $jobId = shift;
	my $filename;
	# Remove mandatory files
	my @extensions = ("mp3");
	foreach my $ext (@extensions) {
		$filename = $archivDir."/".$jobId.".".$ext;
		if (! -r $filename) {
			print "    <P>Unable to find file ".$filename."</P>\n";
		} else {
			unlink($filename) || print "<P>Unable to remove file ".$filename."</P>\n";
		}
	}
	# Remove optional files.
	@extensions = ("txt", "wav", "iso", "toc", "dat");
	foreach my $ext (@extensions) {
		$filename = $archivDir."/".$jobId.".".$ext;
		if (-r $filename) {
			unlink($filename);
		}
	}
	print "          <P>".$jobId." wurde gel&ouml;scht.</P>\n";

}

sub burn()
{
	my $jobId = shift;
	my $filename = $archivDir."/".$jobId.".mp3";
	my $firstLine = 1;
	my $cmd;
	my $res;

	if (! -r $filename) {
		print "    <P>Unable to find file ".$filename."</P>\n";
	} else {
		&show_jobDate($jobId);
		&show_jobinfo($jobId);
		my $scriptName = &RCGI::scriptName();
		print << "EOT";
    <FORM METHOD="post" action="$scriptName">
	<UL>
	  <LI>Pr&uuml;fen, ob eine CD-R(W) im Schacht liegt.</LI>
	</UL>
EOT
		print "<PRE>\n";
		print "### Ejecting device for check.\n";
		$cmd = "eject ".$cdDevice;
		print $cmd."\n";
		$res = system($cmd." 2>&1");
		if ($res != 0) {
			print "\n";
			print "### Error. Ejecting CD.\n";
			print "\n";
			$cmd = "eject ".$cdDevice;
			print "\n(".system($cmd).")\n";
			return;
		}
		print "</PRE>\n";
		print << "EOT";
    <P><input type=submit name=\"reallyburn\" value=\"Brennen beginnen.\">
    <input type=submit name=\"dontburn\" value=\"Abbrechen.\">
EOT
		print "    <input type=\"hidden\" name=\"jobId\" value=\"".$jobId."\"></P>\n";
		print << "EOT";
	</FORM>
EOT
	}
}

sub dontburn()
{
	my $cmd;
	my $res;

	print "<PRE>";
	print "### Loading CD device.\n";
	$cmd = "eject -t ".$cdDevice;
	print "\n";
	print $cmd."\n";
	$res = system($cmd." 2>&1");
	if ($res != 0) {
		print "\n";
		print "### Error. Ejecting CD.\n";
		print "\n";
		$cmd = "eject ".$cdDevice;
		print "\n(".system($cmd).")\n";
		return;
	}
	print "</PRE>\n";
}

sub getMp3Info()
{
	my $jobId = shift;
	my $album = "";
	my $artist = "";
	my $title = "";
	my $comment = "";

	open(DATA, "exiftool $archivDir/$jobId.mp3  |") || die "Unable to read data from exiftool";
	while (<DATA>) {
		my $line = $_;
		# Remove line ends
		$line =~ s/\s*$//g;
		if ($line =~ /^Album\s+: (.*)$/) {
			$album = $1;
		}
		if ($line =~ /^Artist\s+: (.*)$/) {
			$artist = $1;
		}
		if ($line =~ /^Title\s+: (.*)$/) {
			$title = $1;
		}
		if ($line =~ /^Comment\s+: (\([^\)]+\)\s*)(.*)$/) {
			$comment = $2;
		}
	}
	close(DATA);

	return ($album, $artist, $title, $comment);
}

sub reallyburn()
{
	my $jobId = shift;
	my $cmd;
	my $res;
	# multisession info
	my $msinfo;

	my ($album, $artist, $title, $comment) = &getTextInfo($jobId);

	print << 'EOT';
	<script type="text/javascript">
		<!--
		startScroll();
		-->
	</script>
EOT
	print "<PRE>";
	print "### Loading CD device.\n";
	$cmd = "eject -t ".$cdDevice;
	print $cmd."\n";
	print "\n(".system($cmd).")\n";
	print "\n";

	if (! -r $archivDir."/".$jobId.".wav") {
		print "\n";
		print "### Decode MP3 to temporary wav.\n";
		$cmd = "ffmpeg -i ".$archivDir."/".$jobId.".mp3 -ac 2 -acodec pcm_s16le -ar 44100 ".$archivDir."/".$jobId.".wav";
		print $cmd."\n";
		$res = system($cmd." 2>&1");
		print "\n(".$res.")\n";
		if ($res != 0) {
			print "\n";
			print "### Error.\n";
			print "\n";
			return;
		}
		print "\n";
	}
	print "\n";

	if (! -e $archivDir."/".$jobId.".txt") {
		print "### Creating info TXT file.\n";
		print "\n";
		&updateMp3InfoTxt($jobId)
	}

	if (! -e $archivDir."/".$jobId.".toc") {
		$album = &cdtextConvert($album);
		$title = &cdtextConvert($title);
		$artist = &cdtextConvert($artist);
		$comment = &cdtextConvert($comment);
		print "### Creating cdrdao TOC file.\n";
		print "\n";
		open(TOC, ">".$archivDir."/".$jobId.".toc");
		my $toc = "";
		$toc .= "CD_ROM_XA\n";
		$toc .= "\n";
		$toc .= "CD_TEXT {\n";
		$toc .= "  LANGUAGE_MAP {\n";
		$toc .= "    0 : EN\n";
		$toc .= "  }\n";
		$toc .= "\n";
		$toc .= "  LANGUAGE 0 {\n";
		$toc .= "    TITLE \"".$album."\"\n";
		$toc .= "    PERFORMER \"".$artist."\"\n";
		$toc .= "    MESSAGE \"".$comment."\"\n";
		$toc .= "    GENRE \"Speech\"\n";
		$toc .= "  }\n";
		$toc .= "}\n";
		$toc .= "\n";
		$toc .= "TRACK AUDIO\n";
		$toc .= "  CD_TEXT {\n";
		$toc .= "    LANGUAGE 0 {\n";
		$toc .= "      TITLE \"".$title."\"\n";
		$toc .= "      PERFORMER \"".$artist."\"\n";
		$toc .= "      MESSAGE \"".$comment."\"\n";
		$toc .= "    }\n";
		$toc .= "  }\n";
		$toc .= "  FILE \"".$archivDir."/".$jobId.".wav\" 0\n";
		$toc .= "\n";

		print TOC $toc;
		close(TOC);
	}

	print "\n";
	print "### Start burning CD with audio track.\n";
	print "\n";
	open (TOC, "<".$archivDir."/".$jobId.".toc");
	while (<TOC>) {
		print $_;
	}
	close (TOC);
	print "\n";
	$cmd = "cdrdao write -v 2 --device ".$cdDevice;
	$cmd .= " --driver generic-mmc:0x10";
	$cmd .= " --multi";
	$cmd .= " ".$archivDir."/".$jobId.".toc";
	print $cmd."\n";
	$res = system($cmd." 2>&1");
	print "\n(".$res.")\n";
	if ($res != 0) {
		print "\n";
		print "### Error. Ejecting CD.\n";
		print "\n";
		$cmd = "eject ".$cdDevice;
		print $cmd."\n";
		$res = system($cmd." 2>&1");
		print "\n(".$res.")\n";
		if ($res != 0) {
			print "\n";
			print "### Error. Ejecting CD.\n";
			print "\n";
			$cmd = "eject ".$cdDevice;
			print $cmd."\n";
			print "\n(".system($cmd).")\n";
			return;
		}
		return;
	}

	if (! -e $archivDir."/".$jobId.".iso") {
		print "\n";
		print "### Creating data track.\n";
		print "\n";
		$cmd = "cdrecord dev=".$cdDevice." -msinfo";
		$msinfo = qx($cmd);
		$msinfo =~ s/\s*$//g;
		print "\n";
		print "### Found multisession info ".$msinfo.".\n";
		print "\n";
		$cmd = "cd ".$archivDir." && mkisofs -J -R -C ".$msinfo." -o ".$jobId.".iso ";
		$cmd .= $jobId.".mp3 ".$jobId.".txt";
		print $cmd."\n";
		$res = system($cmd." 2>&1");
		if ($res != 0) {
			print "\n";
			print "### Error. Creating CD image.\n";
			print "\n";
			$cmd = "eject ".$cdDevice;
			print "\n(".system($cmd).")\n";
			return;
		}
	}

	print "\n";
	print "### Start burning CD data track.\n";
	print "\n";
	$cmd = "cdrecord -v dev=".$cdDevice." gracetime=5 -tao -eject -pad -data ".$archivDir."/".$jobId.".iso";
	print $cmd."\n";
	$res = system($cmd." 2>&1");
	print "\n(".$res.")\n";
	if ($res != 0) {
		print "\n";
		print "### Error. Ejecting CD.\n";
		print "\n";
		$cmd = "eject ".$cdDevice;
		print $cmd."\n";
		print "\n(".system($cmd).")\n";
		return;
	}

	print "</PRE>\n";
}

sub cdtextConvert()
{
	my $text = shift;

	# trim the string
	$text =~ s/\s*$//;
	$text =~ s/^\s*//;

	# Convert the known Umlauts
	# to support latin-1 standard CD players as well as
	# UTF8-aware software players.
	$text =~ s/Ä/AE/g;
	$text =~ s/Ö/OE/g;
	$text =~ s/Ü/UE/g;
	$text =~ s/ä/ae/g;
	$text =~ s/ö/oe/g;
	$text =~ s/ü/ue/g;
	$text =~ s/ß/ss/g;

	# Trow away all other character decorations.
	from_to($text, "utf8", "latin1");

	# truncate strings to maximum allowable length
	$text = substr($text, 0, 64);

	return $text;
}

sub erase()
{
	my $cmd;
	my $res;
	my $scriptName = &RCGI::scriptName();

	print << "EOT";
    <FORM METHOD="post" action="$scriptName">
	<UL>
	  <LI>Pr&uuml;fen, ob eine CD-RW im Schacht liegt.</LI>
	</UL>
EOT
	print "<PRE>\n";
	print "### Ejecting device for check.\n";
	$cmd = "eject ".$cdDevice;
	print $cmd."\n";
	$res = system($cmd." 2>&1");
	print "\n(".$res.")\n";
	if ($res != 0) {
		print "\n";
		print "### Error. Ejecting CD.\n";
		print "\n";
		$cmd = "eject ".$cdDevice;
		print $cmd."\n";
		print "\n(".system($cmd).")\n";
		return;
	}
	print "</PRE>\n";
	print << "EOT";
	<P><input type=\"radio\" name=\"blank\" value=\"fast\" checked=\"checked\">Schnell-L&ouml;schung</P>
	<P><input type=\"radio\" name=\"blank\" value=\"all\">Komplett-L&ouml;schung</P>
    <P><input type=submit name=\"reallyerase\" value=\"CD-RW: L&ouml;schen beginnen.\">
    <input type=submit name=\"donterase\" value=\"Abbrechen.\"></P>
	</FORM>
EOT
}

sub reallyerase()
{
	my $cmd;
	my $res;
	my $blankmode=shift;

	if (($blankmode eq "fast") || ($blankmode eq "all")) {
		print << 'EOT';
	<script type="text/javascript">
		<!--
		startScroll();
		-->
	</script>
EOT
		print "<PRE>";
		print "### Loading CD device.\n";
		$cmd = "eject -t ".$cdDevice;
		print "\n";
		print "### Start erasing.\n";
		print "\n";
		$cmd = "cdrecord -v dev=".$cdDevice." gracetime=5 -eject blank=".$blankmode;
		print $cmd."\n";
		$res = system($cmd." 2>&1");
		print "\n(".$res.")\n";
		if ($res != 0) {
			print "\n";
			print "### Error. Ejecting CD.\n";
			print "\n";
			$cmd = "eject ".$cdDevice;
			print $cmd."\n";
			print "\n(".system($cmd).")\n";
			return;
		}
		print "</PRE>\n";
	} else {
		print "    <P>Invalid blank mode: ".$blankmode."</P>\n";
	}
}

sub edit_file()
{
	my $jobId = shift;
	my $filename = $archivDir."/".$jobId.".mp3";
	my $scriptName = &RCGI::scriptName();
	if (! -r $filename) {
		print "    <P>Unable to find file ".$filename."</P>\n";
	} else {
		print << "EOT";
    <H1>Aufnahmeinformation bearbeiten</H1>
    <FORM METHOD="post" action="$scriptName">
EOT
		&show_jobDate($jobId);
		&show_jobinfo($jobId, 'input');

    	print "    <P><input type=\"submit\" name=\"save\" value=\"Speichern\">\n";
    	print "    <input type=\"submit\" name=\"dontSave\" value=\"Abbrechen\">\n";
    	print "    <input type=\"hidden\" name=\"jobId\" value=\"".$jobId."\"></P>\n";
		print "    </FORM>\n";
	}
}

sub save_file()
{
	my $jobId = shift;
	my $filename = $archivDir."/".$jobId.".mp3";
	if (! -r $filename) {
		print "    <P>Unable to find file ".$filename."</P>\n";
	} else {
		my $album= scalar $cgi->param("text_veranstalter");
		$album =~ s/\s*$//;
		$album =~ s/'/'\\''/g;
		my $theme = scalar $cgi->param("text_thema");
		$theme =~ s/\s*$//;
		$theme =~ s/'/'\\''/g;
		my $author = scalar $cgi->param("text_referent");
		$author =~ s/\s*$//;
		$author =~ s/'/'\\''/g;
		my $comment = scalar $cgi->param("text_notes");
		$comment =~ s/\s*$//;
		$comment =~ s/'/'\\''/g;
		my ($year, $date, $time, $duration) = &getJobDate($jobId);

		# FIXME: This in fact does not update the info read by exiftool!?
		my $ret = system("mp3info -f -y '$year' -l '$album' -t '$theme' -a '$author' -c '$comment' '$filename' 2>&1");
		print ("mp3info -f -y '.$year.' -l '$album' -t '$theme' -a '$author' -c '$comment' '$filename' 2>&1\n");
		if ($ret != 0) {
			print "Unable to update ".$filename."\n";
		} else {
			print "    <P>Updated Info for ",
				&jobName(scalar $cgi->param("jobId")).".</P>\n";
			# Update TXT file.
			&updateMp3InfoTxt($jobId);
			# Delete toc file. It will be re-generated.
			if ( -f $archivDir."/".$jobId.".toc") {
				unlink($archivDir."/".$jobId.".toc");
			}
		}
	}
}

sub cleanup()
{
	print "          <PRE>\n";
	my @files = glob("$archivDir/*.wav");
	foreach my $filename (@files) {
		if (! -r $filename) {
			print "##### ! Unable to find file ".$filename."!\n";
		} else {
			unlink($filename) || print "##### ! Unable to remove file ".$filename."!\n";
			print $filename." wurde gel&ouml;scht.\n";
		}
	}
	@files = glob("$archivDir/*.iso");
	foreach my $filename (@files) {
		if (! -r $filename) {
			print "##### ! Unable to find file ".$filename."!\n";
		} else {
			unlink($filename) || print "##### ! Unable to remove file ".$filename."!\n";
			print $filename." wurde gel&ouml;scht.\n";
		}
	}
	print "</PRE>\n";
}

sub getJobDate()
{
	my $jobId = shift;
	my $mp3Filename = $jobId.".mp3";
	my $datFilename = $jobId.".dat";
	my $year;
	my $date;
	my $time;
	my $duration = 0;

	if (! -f $archivDir."/".$datFilename) {
		$duration = `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $archivDir/$mp3Filename 2>&1`;
		# Strip milliseconds
		$duration =~ s/\..*//g;
		my $durationText = (int($duration / 60)).":";
		if (($duration % 60) < 10) {
			$durationText .= "0";
		}
		$durationText .= ($duration % 60);
		
		$mp3Filename =~ /^$wavFilePrefix-((\d{4})-\d{2}-\d{2})T(\d{2}_\d{2}_\d{2})\.mp3/;
		$date = $1;
		$year = $2;
		$time = $3;
		$time =~ s/_/:/g;

		$year =~ s/(\d{4}).*/$1/;

		open (DAT, ">".$archivDir."/".$datFilename) || die "Unable to write $datFilename cache";
		print DAT $year."\n";
		print DAT $date."\n";
		print DAT $time."\n";
		print DAT $durationText."\n";
		close (DAT);
	} else {
		open (DAT, "<".$archivDir."/".$datFilename) || die "Unable to read $datFilename cache".
		my @rest;
		($year, $date, $time, $duration, @rest) = <DAT>;
		close (DAT);
	}

	return ($year, $date, $time, $duration);
}

sub show_jobDate()
{
	my $jobId = shift;

	my ($file_year, $file_date, $file_time, $duration) = &getJobDate($jobId);

	print "          <p><b>$file_date<br />\n";
	print "             <i>$file_time</i></b><br />\n";
	print "          (".$duration.")</p>";
}

sub updateMp3InfoTxt()
{
	my $jobId = shift;
	my ($album, $artist, $title, $comment) = &getMp3Info($jobId);

	open(TXT, ">".$archivDir."/".$jobId.".txt") || die "Unable to write ".$jobId.".txt";
	print TXT "$album\n";
	print TXT "$title\n";
	print TXT "$artist\n";
	print TXT "$comment\n";
	close(TXT);
}

sub getTextInfo()
{
	my $jobId = shift;

	open (TXT, "< ".$archivDir."/".$jobId.".txt") || die "unable to read ".$archivDir."/".$jobId.".txt";
	my ($album, $artist, $title, $comment, @rest) = <TXT>;
	close (TXT);

	return ($album, $artist, $title, $comment);
}

sub show_jobinfo()
{
	my $jobId = shift;
	my $style = shift;

	my ($album, $artist, $title, $comment) = &getTextInfo($jobId);

	if (defined $style && $style eq "input") {
		print "<p>Veranstalter:<br />\n";
		print '<input type="text" size="30" maxlength="'.$cdtextMaxSize.'" value="'.$album.'" name="text_veranstalter"></p>'."\n";
		print "<p>Titel:<br />\n";
		print '<input type="text" size="30" maxlength="'.$cdtextMaxSize.'" value="'.$title.'" name="text_thema"></p>'."\n";
		print "<p>Referent:<br />\n";
		print '<input type="text" size="30" maxlength="'.$cdtextMaxSize.'" value="'.$artist.'" name="text_referent"></p>'."\n";
		print "<p>Textbezug:<br />\n";
		print '<input type="text" size="30" maxlength="'.$cdtextMaxSize.'" name="text_notes" value="'.$comment.'"></p>'."\n";
	} else {
		print "<p>\n";
		print "  <b>$title</b><br />\n";
		print "  <i>$artist</i><br />\n";
		print "  $comment\n";
		print "</p>\n";
	}
}


sub show_list()
{
	my @files = reverse(glob("$archivDir/*.mp3"));
	my $scriptName = &RCGI::scriptName();
	# Print free space info.
	&RCGI::RCGI_printFree;
	# Check for records.
	if (@files < 1) {
		print "    <P>Keine Aufnahmen verf&uuml;gbar.</P>\n";
	} else {
		print "    <TABLE CELLPADDING=1 BORDER=1>\n";
		print "      <TR>\n";
		print "        <TH>\n";
		print "          Optionen\n";
		print "        </TH>\n";
		print "        <TH>\n";
		print "          Datum\n";
		print "        </TH>\n";
		print "        <TH>\n";
		print "          Info\n";
		print "        </TH>\n";
		print "        <TH>\n";
		print "          Download\n";
		print "        </TH>\n";
		print "      </TR>\n";
		foreach my $filename (@files) {
			my $jobId = $filename;
			my @fileInfo = stat($filename);
			$jobId =~ s/^.*\/([^\/]+)\.mp3$/$1/;
			my $firstLine = 1;
			print "      <TR>\n";
			print "        <TD>\n";
			print "          <FORM METHOD=POST action=\"$scriptName\">\n";
			print "          <p>";
 	   		#print "          <input type=\"submit\" name=\"edit\" value=\"Bearbeiten\"><BR>\n";
    			print "          <input type=\"submit\" name=\"burn\" value=\"Brennen\"><BR>\n";
    			print "          <input type=\"submit\" name=\"remove\" value=\"Entfernen\">\n";
	    		print "          <input type=\"hidden\" name=\"jobId\" value=\"".$jobId."\"></P>\n";
			print "          </FORM>\n";
			print "        </TD>\n";
			print "        <TD VALIGN=\"top\">\n";
			&show_jobDate($jobId);
			print "        </TD>\n";
			print "        <TD VALIGN=\"top\">\n";
			&show_jobinfo($jobId);
			print "        </TD>\n";
			print "        <TD VALIGN=\"top\">\n";
			print "          <p><a href=\"".$archivDir."/".$jobId.".mp3\">Sound (MP3)</a>\n";
			if ( -r $archivDir."/".$jobId.".wav") {
				print "  <br /><a href=\"".$archivDir."/".$jobId.".wav\">Sound (WAV)</a>\n";
			}
			if ( -r $archivDir."/".$jobId.".txt") {
				print "  <br /><a href=\"".$archivDir."/".$jobId.".txt\">Info TXT</a>\n";
			}
			if ( -r $archivDir."/".$jobId.".iso") {
				print "  <br /><a href=\"".$archivDir."/".$jobId.".iso\">MP3+TXT ISO</a>\n";
			}
			print "          </p>\n";
			print "        </TD>\n";
			print "      </TR>\n";
		}
		print "    </TABLE>\n";
  		print "    <P><A HREF=\"?cleanup=wav\">Zwischenformat-Dateien (*.wav, *.iso) entfernen, um Platz zu sparen</A></P>\n";
	}
}

sub jobName()
{
	my $jobname = shift;
	$jobname =~ s/T/ /;
	$jobname =~ s/^$wavFilePrefix-//;
	return $jobname;
}

}
