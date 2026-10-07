#!/usr/bin/perl
use strict;
use warnings;

use Dpkg::Checksums;
use Dpkg::Control qw(CTRL_DSC CTRL_FILE_BUILDINFO CTRL_FILE_CHANGES);
use Dpkg::Source::Package;
use File::Basename qw(basename dirname);
use File::Glob qw(bsd_glob);

my ($packages, @sources) = @ARGV;
die "Usage: verify-source-packages.pl PACKAGES SOURCE_DIR [SOURCE_DIR ...]\n"
    unless defined $packages && @sources;

for my $source (qw(miubomz-settings calamares)) {
    my @descriptors = map { bsd_glob("$_/${source}_*.dsc") } @sources;
    die "Expected one complete $source source package.\n" unless @descriptors == 1;
    my $descriptor = $descriptors[0];
    my $control = Dpkg::Control->new(type => CTRL_DSC);
    $control->load($descriptor);
    die "Source descriptor identity differs from $source.\n" unless $control->{Source} eq $source;
    Dpkg::Source::Package->new(filename => $descriptor,
        options => { require_strong_checksums => 1 })->check_checksums();
    my $directory = dirname($descriptor);
    my $version = $control->{Version};
    $version =~ s/^\d+://;
    my @binaries = sort split /[\s,]+/, $control->{Binary};

    for my $extension (qw(changes buildinfo)) {
        my @records = bsd_glob("$directory/${source}_${version}_*.$extension");
        die "Expected one $source .$extension build record.\n" unless @records == 1;
        my $record = Dpkg::Control->new(type => $extension eq 'changes'
            ? CTRL_FILE_CHANGES : CTRL_FILE_BUILDINFO);
        $record->load($records[0]);
        die "Build record identity differs from its source descriptor: $records[0]\n"
            unless $record->{Source} eq $control->{Source}
                && $record->{Version} eq $control->{Version}
                && join(' ', sort split /[\s,]+/, $record->{Binary}) eq join(' ', @binaries);
        my $checksums = Dpkg::Checksums->new();
        $checksums->add_from_control($record);
        my @files = $checksums->get_files();
        die "Build record has no file checksums: $records[0]\n" unless @files;
        die "Build record omits its source descriptor: $records[0]\n"
            unless grep { $_ eq basename($descriptor) } @files;
        my $buildinfo = basename($records[0]);
        $buildinfo =~ s/\.changes$/.buildinfo/;
        die "Changes record omits its build information: $records[0]\n"
            if $extension eq 'changes' && !grep { $_ eq $buildinfo } @files;
        for my $filename (@files) {
            die "Build record lacks strong checksums for $filename.\n"
                unless $checksums->has_strong_checksums($filename);
            my $path = $filename =~ /\.deb$/ ? "$packages/$filename" : "$directory/$filename";
            $checksums->add_from_file($path, key => $filename);
        }
    }
    print "Verified $source source package and native build records.\n";
}
