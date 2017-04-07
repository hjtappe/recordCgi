#!/usr/bin/env perl
use strict;
use warnings;
use CGI::Carp qw(fatalsToBrowser);
BEGIN {
	my $cdtextMaxSize = 64;
	# add the path to the perl module to @INC.
	my $mydir = `dirname $0`;
	$mydir =~ s/\r?\n$//;
	push(@INC, $mydir);
	require recordCgi;
	
	my $rcgi = new RCGI();

	$| = 1;
	use CGI;
	my $cgi = new CGI;
	my $wavFilePrefix = "tm";
	my $transcodeScript = &RCGI::transcoder();
	my $wavDir = &RCGI::spoolDir();

#	print "Content-type: text/plain\n\n";
	print "Content-type: text/html\n\n";
	my $scriptName = &RCGI::scriptName();

	&RCGI::printHeader("recordCGI: Aufnahme archivieren");
	print << "EOT";
  <P ALIGN=RIGHT><A HREF="help.htm">Dokumentation</A></P>
  <P><A HREF="list.cgi">Zum Archiv</A><BR>
  <A HREF="$scriptName">Aktualisieren</A></P>
EOT
	if (defined($cgi->param("save"))) {
		&saveFile(scalar $cgi->param("jobId"));
		&show_list;
	} elsif (defined($cgi->param("unselect"))) {
		&unselect(scalar $cgi->param("jobId"));
		&show_list;
	} elsif (defined($cgi->param("remove"))) {
		&remove(scalar $cgi->param("jobId"));
	} elsif (defined($cgi->param("reallyremove"))) {
		&reallyRemove(scalar $cgi->param("jobId"));
		&show_list;
	} elsif (defined($cgi->param("transcode"))) {
		&show_list;
		&startTranscode;
	} else {
		&show_list;
	}

	&RCGI::printTrailer;

sub show_list()
{
	my $searchstring = $wavDir."/".$wavFilePrefix."-*T*.w64";
	my @wavFiles = glob($searchstring);
	my $items = 0;
	my $spoolCnt = 0;
	# Print free space info.
	&RCGI::RCGI_printFree;
	print "    <FORM METHOD=POST action=\"".&RCGI::scriptName()."\">\n";
	if (@wavFiles < 1) {
		print "    <P>Keine Aufnahmen in '".$searchstring."' verf&uuml;gbar. Is the directory readable for the web server?</P>\n";
	} else {
		print << "EOT";
    <TABLE CELLPADDING=5 BORDER=0>
        <TR>
          <TH ROWSPAN=2>
            &nbsp;
          </TH>
          <TH ROWSPAN=2 ALIGN=LEFT VALIGN=BOTTOM>
            Job Name
          </TH>
          <TH COLSPAN=3>
            Gr&ouml;&szlig;e
          </TH>
          <TH ROWSPAN=2>
            Zeit (ca.)
          </TH>
        </TR>
        <TR>
          <TH>
            Bytes
          </TH>
          <TH>
            kBytes
          </TH>
          <TH>
            MBytes
          </TH>
        </TR>
EOT
		foreach my $filename (@wavFiles) {
			print "        <TR><TD>&nbsp;</TD><TD><HR></TD><TD COLSPAN=3>&nbsp;</TD></TR>\n";
			my $spooling = 0;
			my $txtFile = $filename;
			$txtFile =~ s/\.w64$/.txt/;
			if (-e $txtFile) {
				$spooling = 1;
				$spoolCnt ++;
			}
			my $jobId = $filename;
			$jobId =~ s/^.*\/([^\/]+)\.w64$/$1/;
			my $jobFile = "/var/lock/".$jobId.".txt";
			my @fileInfo = stat($filename);
			my @timeInfo = localtime($fileInfo[9]);
			$timeInfo[4] ++;
			foreach (@timeInfo) {
				$_ =~ s/^([0-9])$/0$1/;
			}
			print "      <TR>\n";
			print "        <TD ALIGN=CENTER>\n";
			if ($spooling == 0) {
    			print "          <input type=\"radio\" name=\"jobId\" value=\"".$jobId."\"";
				if ($items == 0) {
					print " checked";
				}
				print">\n";
				$items ++;
			} else {
				if ( -e $jobFile ) {
					print "<FONT SIZE=\"-5\">aktiv</FONT>";
				} else {
					print "<FONT SIZE=\"-5\">gew&auml;hlt<BR>\n";
					print "<A HREF=\"?unselect&jobId=".$jobId."\">abw&auml;hlen</A></FONT>";
				}
			}
			print "        </TD>\n";
			print "        <TD>\n";
			print "          ".&jobName($jobId)." - ",
					($timeInfo[5] + 1900)."-".$timeInfo[4]."-".$timeInfo[3],
					" ".$timeInfo[2].":".$timeInfo[1].":".$timeInfo[0]."\n";
			print "        </TD>\n";
			print "        <TD ALIGN=RIGHT>\n";
			print "          ".$fileInfo[7]."\n";
			print "        </TD>\n";
			print "        <TD ALIGN=RIGHT>\n";
			print "          ".int($fileInfo[7] / 1024).",",
					(($fileInfo[7] % 1024) % 100)."\n";
			print "        </TD>\n";
			print "        <TD ALIGN=RIGHT>\n";
			print "          ".int($fileInfo[7] / (1024 * 1024)).",",
					(($fileInfo[7] % (1024 * 1024)) % 100)."\n";
			print "        </TD>\n";
			print "        <TD ALIGN=RIGHT>\n";
			print "          ".int($fileInfo[7] / (&RCGI::w64Val * 60)).":",
					(($fileInfo[7] / &RCGI::w64Val) % 60)."\n";
			print "        </TD>\n";
			print "      </TR>\n";
		}
		print "        <TR><TD>&nbsp;</TD><TD><HR></TD><TD COLSPAN=3>&nbsp;</TD></TR>\n";
		print "    </TABLE>\n";
	}
	if ($items != 0) {
		my $referent = $rcgi->param("referent");
		if (! defined($referent)) {
			$referent = "Referent Name"
		}
		my $veranstalter = $rcgi->param("veranstalter");
		if (! defined($veranstalter)) {
			$veranstalter = "Veranstalter"
		}
		print << "EOT";
<TABLE BORDER=0 CELLPADDING=5>
      <TR VALIGN=TOP>
	    <TD>Veranstalter:</TD>
	    <TD><input type="text" size="30" maxlength="$cdtextMaxSize"
		name="text_veranstalter" value="$veranstalter"></TD>
	  </TR>
      <TR VALIGN=TOP>
	    <TD>Thema:</TD>
	    <TD><input type="text" size="30" maxlength="$cdtextMaxSize" name="text_thema" /></TD>
	  </TR>
	  <TR VALIGN=TOP>
        <TD>Referent:</TD>
		<TD><input type="text" size="30" maxlength="$cdtextMaxSize" name="text_referent"
		value="$referent"> <input type="checkbox" name="save" value="dosave" /> Save
		</TD>
	  </TR>
	  <TR VALIGN=TOP>
        <TD>Textbezug:</TD>
		<TD><input type="text" size="30" maxlength="$cdtextMaxSize" name="text_notes" value="Bezug: " /></TD>
	  </TR>
	</TABLE>

EOT
	}
	if (@wavFiles >= 1) {
		print "<P>";
		if ($items != 0) {
    		print "<input type=\"submit\" name=\"save\" value=\"Zum Archivieren vormerken\">\n";
		}
		if ($spoolCnt > 0) {
	    	print "<input type=\"submit\" name=\"transcode\" value=\"Archivierung starten\">\n";
		}
		if ($items != 0) {
    		print "<input type=\"submit\" name=\"remove\" value=\"Entfernen\">";
		}
		print "</P>\n";
	}
	print "    </FORM>\n";
}

sub remove()
{
	my $jobId = shift;
	my $filename = $wavDir."/".$jobId.".w64";
	my $firstLine = 1;

	if ($jobId eq "") {
		print "<P><FONT COLOR=\"#FF0000\">Keine Aufnahme ausgew&auml;hlt.</FONT></P>\n";
		&show_list;
	} else {
		if (! -r $filename) {
			print "    <P>Unable to find file ".$filename."</P>\n";
		} else {
			my $scriptName = &RCGI::scriptName();
			print << "EOT";
    <FORM METHOD="post" action="$scriptName">
    <P><input type=submit name=\"reallyremove\" value=\"Wirklich l&ouml;schen\">
    <input type=submit name=\"dontremove\" value=\"Abbrechen\">
EOT
			print "    <input type=\"hidden\" name=\"jobId\" value=\"".$jobId."\">\n";
			print " ".&jobName($jobId)."</P>\n";
			print << "EOT";
	</FORM>
EOT
		}
	}
}

sub reallyRemove()
{
	my $jobId = shift;
	my $filename = $wavDir."/".$jobId.".w64";
	if ($jobId eq "") {
		print "<P><FONT COLOR=\"#FF0000\">Keine Aufnahme ausgew&auml;hlt.</FONT></P>\n";
		&show_list;
	} else {
		if (! -r $filename) {
			print "    <P>Unable to find file ".$filename."</P>\n";
		} else {
			unlink($filename) || die "Unable to remove file ".$filename."\n";
			print "          <P>".&jobName($jobId)." wurde gel&ouml;scht.</A></P>\n";
		}
	}
}

sub unselect()
{
	my $jobId = shift;
	my $filename = $wavDir."/".$jobId.".txt";
	if ($jobId eq "") {
		print "<P><FONT COLOR=\"#FF0000\">Keine Aufnahme ausgew&auml;hlt.</FONT></P>\n";
		&show_list;
	} else {
		if (! -r $filename) {
			print "    <P>Unable to find file ".$filename."</P>\n";
		} else {
			unlink($filename) || die "Unable to remove file ".$filename."\n";
			print "          <P>".&jobName($jobId)." wurde abgew&auml;hlt.</A></P>\n";
		}
	}
}

sub jobName()
{
	my $jobname = shift;
	$jobname =~ s/T/ /;
	$jobname =~ s/^$wavFilePrefix-//;
	return $jobname;
}

sub saveFile()
{
	my $jobId = shift;
	my $filename = $wavDir."/".$jobId.".w64";
	my $textname = $wavDir."/".$jobId.".txt";

	if ($jobId eq "") {
		print "<P><FONT COLOR=\"#FF0000\">Keine Aufnahme ausgew&auml;hlt.</FONT></P>\n";
		&show_list;
	} else {
		if (! -r $filename) {
			print "    <P>Unable to find file ".$filename."</P>\n";
		} else {
			open(DATA, "> ".$textname) ||
				die "Unable to write '".$wavDir."/".$jobId.".txt'!\n";
			my $textEntry = "";
			# Publisher
			$textEntry = scalar $cgi->param("text_veranstalter");
			# remove trailing invisibles
			$textEntry =~ s/\s*$//;
			print DATA $textEntry."\n";
			# Title
			$textEntry = scalar $cgi->param("text_thema");
			# remove trailing invisibles
			$textEntry =~ s/\s*$//;
			print DATA $textEntry."\n";
			# Author
			$textEntry = scalar $cgi->param("text_referent");
			if ($cgi->param("save") &&
					$cgi->param("save") eq "dosave") {
				$rcgi->param("referent", scalar $cgi->param("text_referent"));
				$rcgi->param("veranstalter", scalar $cgi->param("text_veranstalter"));
			}
			$textEntry =~ s/\s*$//;
			print DATA $textEntry."\n";
			# Comment
			$textEntry = scalar $cgi->param("text_notes");
			$textEntry =~ s/\s*$//;
			print DATA $textEntry."\n";
			close(DATA);
		}
	}
}

sub startTranscode()
{
	print << 'EOT';
	<script type="text/javascript">
		startScroll();
	</script>
EOT
	print "<PRE>";
	print "\n(".system($transcodeScript).")";
	print "</PRE>\n";
}

}
