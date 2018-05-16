# ![Pangu](https://github.com/Jianwei-Zhang/LIMS/blob/master/htdocs/images/logo.png) LIMS Docs

## Installation Instruction (draft)

1) Download GPM source files and unzip the file on your own local system.

2) Make a new directory under both /var/www/cgi-bin/ directory and /var/www/html/ directory. For example, the new directory named "lims". The commands are:

`$ mkdir /var/www/cgi-bin/lims`

`$ mkdir /var/www/html/lims`

3) Copy all the files and directories in the "cgi-bin" directory (GPM source directory, e.g. ~/LIMS-master/cgi-bin/) to the /var/www/cgi-bin/lims directory:

`$ cp -r ~/LIMS-master/cgi-bin/* /var/www/cgi-bin/lims/`

4) Copy all the files and directories in the "htdocs" directory (GPM source directory, e.g. ~/LIMS-master/htdocs/) to /var/www/html/lims directory:

`$ cp -r ~/LIMS-master/htdocs/* /var/www/html/lims/`

5) Make all files in /var/www/cgi-bin/lims/ executable: 

`$ chmod 775 /usr/www/cgi-bin/lims/*`

6) Activate the index file, rename the "index.html.tmpl" file in /var/www/html/lims/ directory as "index.html":

`$ mv /var/www/html/lims/index.html.tmpl /var/www/html/lims/index.html`

7) Activate the configuration file, rename the "main.conf.tmpl" file in the /var/www/cgi-bin/lims/ directory as "main.conf":

`$ mv /var/www/cgi-bin/lims/main.conf.tmpl /var/www/cgi-bin/lims/main.conf`

8) Install the following perl modules for GPM: 

`$ cpan SVG`

`$ cpan CGI`

`$ cpan URI-Escape-XS`

`$ cpan Math::Trig`

`$ cpan JSON`

The source of these modules are:

	Scalable Vector Graphics (SVG) Library http://search.cpan.org/dist/SVG/

	CGI http://search.cpan.org/dist/CGI/

	URI-Escape-XS http://search.cpan.org/dist/URI-Escape-XS/

	Math::Trig http://search.cpan.org/~zefram/Math-Complex-1.59/lib/Math/Trig.pm

	JSON http://search.cpan.org/~makamaka/JSON-2.53/lib/JSON.pm

9) Download the blast+(ftp://ftp.ncbi.nih.gov/blast/) then install it in /usr/biosoft/ directory and create symbol link in the /var/www/cgi-bin/lims/ document by using the command: 

`$ ln -s /usr/biosoft/blast+/`

10) Make a new database named "gpm" for GPM by mysql. The command are:

`$ mysql -u root -p`

`Enter password: ********`

`mysql> CREATE DATABASE IF NOT EXISTS gmp;`

`mysql> use gmp;`

`mysql> source /LIMS-master/sql/lims.sql`
	
11) Open the "main.conf" file in /var/www/cgi-bin/lims/ directory and complete the information as follow:

```
	USERNAME = root

	PASSWORD = YOUR PASSWORD OF THE ROOT

	DATABASE = gpm (YOUR DATABASE-NAME YOU CREATED ON STEP 10)

	DBHOST = localhost

	HOSTURL = http://YOUR-HOSTURL

	CGIBINDIR = /var/www/cgi-bin/lims

	CGIBIN = /cgi-bin/lims

	HTMLDIR = /var/www/html/lims

	HTDOCS =  /lims

	DATADIR = /var/www/html/lims/data

	TMPDIR = /var/www/html/lims/data/tmp

	TMPURL = /lims/data/tmp

	JOBDIR = /var/www/html/lims/data/jobs

	VECTOR = /var/www/html/lims/data/pAGIBAC1_HindIII.txt

	VECTORLENGTH = 7522

	POLISHED = /var/www/html/lims/data/polished

	POLISHEDURL = /lims/data/polished
```
Make sure that you enter the correct path of your files and don't forget to bring the directory name you created on step 2. In this text we add "lims" into the path.

12) To optimize GPM, enlarge the number of "max_allowed_packet" (The maximum size of one packet or any generated/intermediate string) to "128M", set "ft_min_word_len" (The minimum length of the word to be included in a MyISAM FULLTEXT index) to "1" in the /etc/my.cnf file. 

13) Visit your local instance at http://YOUR-HOSTURL/lims on your Server. The username and password are "admin/admin".

Before loading data, please make sure the above link is alive. Any questions during installation, please contact Jianwei Zhang (jzhang@mail.hzau.edu.cn).

## Required Programs, JavaScript Libraries and Perl Modules

	BLAST+ ftp://ftp.ncbi.nih.gov/blast/

	Scalable Vector Graphics (SVG) Library http://search.cpan.org/dist/SVG/

	CGI http://search.cpan.org/dist/CGI/

	URI-Escape-XS http://search.cpan.org/dist/URI-Escape-XS/

	Math::Trig http://search.cpan.org/~zefram/Math-Complex-1.59/lib/Math/Trig.pm

	JSON http://search.cpan.org/~makamaka/JSON-2.53/lib/JSON.pm

	JSON::XS http://search.cpan.org/~mlehmann/JSON-XS-3.04/XS.pm

jQuery has been included in this repository, for more details, you can visit

	jQuery http://jquery.com/

	jQuery UI http://jqueryui.com/

## Manual
To be added.



## How to cite
Zhang, J. et al. Genome Puzzle Master (GPM): an integrated pipeline for building and editing pseudomolecules from fragmented sequences. Bioinformatics, 2016, 32 (20): 3058-3064 (https://doi.org/10.1093/bioinformatics/btw370).
