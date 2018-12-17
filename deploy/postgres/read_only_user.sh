#!/bin/sh
#
# The MIT License
#
# Copyright 2014-2017 Jakub Jirutka <jakub@jirutka.cz>.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


usage() {
	cat <<- EOF
		usage: $0 options
		
		This script grants read-only privileges to a specified role on all tables, views
		and sequences in a database schema and sets them as default.
		
		OPTIONS:
		   -h   Show this message
		   -d   Database name
		   -u   Role name
		   -s   Schema (defaults to public)
	EOF
}

pgexec() {
	local cmd=$1
	psql --no-psqlrc --no-align --tuples-only --record-separator=\0 --quiet \
		--echo-queries --command="$cmd" "$DB_NAME"
}


DB_NAME=''
ROLE=''
SCHEMA='public'
while getopts 'hd:u:s:' OPTION; do
	case $OPTION in
		h) usage; exit 1;;
		d) DB_NAME=$OPTARG;;
		u) ROLE=$OPTARG;;
		s) SCHEMA=$OPTARG;;
	esac
done

if [ -z "$DB_NAME" ] || [ -z "$ROLE" ]; then
	usage
	exit 1
fi

pgexec "GRANT CONNECT ON DATABASE $DB_NAME TO $ROLE;
GRANT USAGE ON SCHEMA $SCHEMA TO $ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA $SCHEMA TO $ROLE;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA $SCHEMA TO $ROLE;
ALTER DEFAULT PRIVILEGES IN SCHEMA $SCHEMA GRANT SELECT ON TABLES TO $ROLE;
ALTER DEFAULT PRIVILEGES IN SCHEMA $SCHEMA GRANT SELECT ON SEQUENCES TO $ROLE;"

# Uncomment to also grant privileges on all functions/procedures in the schema.
# It's usually NOT what you want - functions can modify data!
#pgexec "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA $SCHEMA TO $ROLE;
#ALTER DEFAULT PRIVILEGES IN SCHEMA $SCHEMA GRANT EXECUTE ON FUNCTIONS TO $ROLE;"