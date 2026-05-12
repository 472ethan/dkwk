AC_PREREQ([2.71])
AC_INIT([dkwk-engine], [0.20260512])

AC_PATH_PROG([PYTHON3], [python3])
AS_IF([test -z "$PYTHON3"],
      [AC_MSG_ERROR([python3 not found])])

# Autoconf leaves $sysconfdir literally equal to '${prefix}/etc'
# (Makefile expands the references at build time).  We're
# generating a Python file, so resolve here.
test "$prefix"      = NONE && prefix=$ac_default_prefix
test "$exec_prefix" = NONE && exec_prefix='${prefix}'

# If --localstatedir wasn't given, autoconf's default is
# '${prefix}/var', which is almost never the right home for
# system state.  Pick a per-OS convention instead.
case "$localstatedir" in
*'${prefix}'*|*'${exec_prefix}'*)
	case `uname -s 2>/dev/null` in
	Linux)                               localstatedir=/var/lib ;;
	FreeBSD|DragonFly|NetBSD|OpenBSD)    localstatedir=/var/db ;;
	# Fall through other OSes. (for now...)
	esac
	AC_MSG_NOTICE([defaulting --localstatedir to $localstatedir])
	;;
esac

eval sysconfdir=\"$sysconfdir\"
eval localstatedir=\"$localstatedir\"

# Quote each path as a Python string literal so the generated
# config.py is valid Python regardless of what's in the path.
sysconfdir_py3=`$PYTHON3 -c 'import sys; print(ascii(sys.argv[[1]]))' "$sysconfdir"`
localstatedir_py3=`$PYTHON3 -c 'import sys; print(ascii(sys.argv[[1]]))' "$localstatedir"`
AC_SUBST([sysconfdir_py3])
AC_SUBST([localstatedir_py3])

AC_CONFIG_FILES([dkwk/config.py])
AC_OUTPUT
