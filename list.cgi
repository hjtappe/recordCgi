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
	my $cgi = new CGI;
	my $archivDir = "Archiv";
	my $wavFilePrefix = "tm";
	my $cdDevice = "/dev/cdrw";

	# add the path to the perl module to @INC.
	my $mydir = `dirname $0`;
	$mydir =~ s/\s*$//g;
	$mydir =~ s/\r?\n$//;
	push(@INC, $mydir);
	require recordCgi;
	my $scriptName = &RCGI::scriptName();

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
	@extensions = ("txt", "wav", "iso", "toc");
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
	my $artist = "";
	my $title = "";
	my $comment = "";

	open(DATA, "exiftool $archivDir/$jobId.mp3  |") || die "Unable to read data from exiftool";
	while (<DATA>) {
		my $line = $_;
		# Remove line ends
		$line =~ s/\s*$//g;
		if ($line =~ /^Comment\s+: (\([^\)]+\))(.*)$/) {
			$comment = $2;
		}
		if ($line =~ /^Artist\s+: (.*)$/) {
			$artist = $1;
		}
		if ($line =~ /^Title\s+: (.*)$/) {
			$title = $1;
		}
	}
	close(DATA);

	return ($artist, $title, $comment);
}

sub reallyburn()
{
	my $jobId = shift;
	my $cmd;
	my $res;
	# multisession info
	my $msinfo;
	my ($artist, $title, $comment) = &getMp3Info($jobId);

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
		$cmd = "mpg321 --stereo --wav ".$archivDir."/".$jobId.".wav ".$archivDir."/".$jobId.".mp3";
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

	if (! -e $archivDir."/".$jobId.".toc") {
		print "### Creating info TXT file.\n";
		print "\n";
		&show_jobinfo($jobId, "txt");
	}

	if (! -e $archivDir."/".$jobId.".toc") {
		print "### Creating cdrdao TOC file.\n";
		print "\n";
		open(TOC, ">".$archivDir."/".$jobId.".toc");
		print TOC << "EOT";
CD_DA

CD_TEXT {
  LANGUAGE_MAP {
    0 : DE
  }

  LANGUAGE 0 {
    TITLE "$title"
    PERFORMER "$artist"
	MESSAGE "$comment"
	GENRE "Speech"
  }
}

TRACK AUDIO
  START
  CD_TEXT {
    LANGUAGE 0 {
      TITLE "$title"
      PERFORMER "$artist"
	  MESSAGE "$comment"
	  GENRE "Speech"
    }
  }
  FILE "$archivDir/$jobId.wav" 0
EOT
		close(TOC);
	}

	print "\n";
	print "### Start burning CD audio track.\n";
	print "\n";
	$cmd = "cdrdao write -v 2 --device ".$cdDevice." --driver generic-mmc-raw";
	$cmd .= " --multi --speed=10 ".$archivDir."/".$jobId.".toc";
	print $cmd."\n";
	$res = system($cmd." 2>&1");
	print "\n(".$res.")\n";
	if ($res != 0) {
		print "\n";
		print "### Error. Ejecting CD.\n";
		print "\n";
		$cmd = "eject ".$cdDevice;
		$res = system($cmd." 2>&1");
		print "\n(".$res.")\n";
		if ($res != 0) {
			print "\n";
			print "### Error. Ejecting CD.\n";
			print "\n";
			$cmd = "eject ".$cdDevice;
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
		print "\n(".system($cmd).")\n";
		return;
	}

	print "</PRE>\n";
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
	$res = system($cmd." 2>&1");
	print "\n(".$res.")\n";
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
		my $author = scalar $cgi->param("text_referent");
		$author =~ s/\s*$//;
		$author =~ s/'/'\\''/g;
		my $theme = scalar $cgi->param("text_thema");
		$theme =~ s/\s*$//;
		$theme =~ s/'/'\\''/g;
		my $comment = scalar $cgi->param("text_notes");
		$comment =~ s/\s*$//;
		$comment =~ s/'/'\\''/g;
		my $ret = system("mp3info -f -t '$theme' -a '$author' -c '$comment' '$filename' 2>&1");
		if ($ret != 0) {
			print "Unable to update ".$filename."\n";
		} else {
			print "    <P>Updated Info for ",
				&jobName(scalar $cgi->param("jobId")).".</P>\n";
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


sub show_jobDate()
{
	my $jobId = shift;

	my $filename = $jobId.".mp3";
	my $duration = 0;

	# Strip milliseconds
	$duration = `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $archivDir/$filename`;
	$duration =~ s/\..*//g;

	$filename =~ /^$wavFilePrefix-(\d{4}-\d{2}-\d{2})T(\d{2}_\d{2}_\d{2})\.mp3/;
	my $file_date = $1;
	my $file_time = $2;
	$file_time =~ s/_/:/g;
	print "          <p><b>$file_date<br /><i>$file_time</i></b><br />";
	print "          (".(int($duration / 60)).":".($duration % 60).")</p>";
}


sub show_jobinfo()
{
	my $jobId = shift;
	my $style = shift;

	my $filename = $jobId.".mp3";
	my ($artist, $title, $comment) = &getMp3Info($jobId);

	if (defined $style && $style eq "input") {
		print "<p>Titel:<br />\n";
		print '<input type="text" size="30" maxlength="30" value="'.$title.'" name="text_thema"></p>'."\n";
		print "<p>Referent:<br />\n";
		print '<input type="text" size="30" maxlength="30" value="'.$artist.'" name="text_referent"></p>'."\n";
		print "<p>Textbezug:<br />\n";
		print '<input type="text" size="30" maxlength="30" name="text_notes" value="'.$comment.'"></p>'."\n";
	} elsif (defined $style && $style eq "txt") {
		open(TXT, ">".$archivDir."/".$jobId.".txt");
		print TXT "             <b>$title</b><br />\n";
		print TXT "             <i>$artist</i><br />\n";
		print TXT "             $comment\n";
		close(TXT);
	} else {
		print "<p>\n";
		print "             <b>$title</b><br />\n";
		print "             <i>$artist</i><br />\n";
		print "             $comment\n";
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
 	   		print "          <input type=\"submit\" name=\"edit\" value=\"Bearbeiten\"><BR>\n";
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
				print "  <br /><a href=\"".$archivDir."/".$jobId.".txt\">TXT</a>\n";
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
