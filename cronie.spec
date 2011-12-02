%bcond_without selinux
%bcond_without pam
%bcond_without audit
%bcond_without inotify

Summary: Cron daemon for executing programs at set times
Name: cronie
Version: 1.4.4
Release: 2%{?dist}
License: MIT and BSD and ISC and GPLv2
Group: System Environment/Base
URL: https://fedorahosted.org/cronie
Source0: https://fedorahosted.org/releases/c/r/cronie/%{name}-%{version}.tar.gz
Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: syslog, bash >= 2.0
Requires: /usr/sbin/sendmail
Conflicts: sysklogd < 1.4.1
Provides: vixie-cron = 4:4.4
Obsoletes: vixie-cron <= 4:4.3
Requires: dailyjobs

%if %{with selinux}
Requires: libselinux >= 2.0.64
Buildrequires: libselinux-devel >= 2.0.64
%endif
%if %{with pam}
Requires: pam >= 1.0.1
Buildrequires: pam-devel >= 1.0.1
%endif
%if %{with audit}
Buildrequires: audit-libs-devel >= 1.4.1
%endif

Requires(post): /sbin/chkconfig coreutils sed
Requires(postun): /sbin/chkconfig
Requires(postun): /sbin/service 
Requires(preun): /sbin/chkconfig 
Requires(preun): /sbin/service

%description
Cronie contains the standard UNIX daemon crond that runs specified programs at
scheduled times and related tools. It is a fork of the original vixie-cron and
has security and configuration enhancements like the ability to use pam and
SELinux.

%package anacron
Summary: Utility for running regular jobs
Requires: crontabs
Group: System Environment/Base
Provides: dailyjobs
Provides: anacron = 2.4
Obsoletes: anacron <= 2.3
Requires(post): coreutils
Requires: %{name} = %{version}-%{release}

%description anacron
Anacron became part of cronie. Anacron is used only for running regular jobs.
The default settings execute regular jobs by anacron, however this could be
overloaded in settings.

%package noanacron
Summary: Utility for running simple regular jobs in old cron style
Group: System Environment/Base
Provides: dailyjobs
Requires: crontabs
Requires: %{name} = %{version}-%{release}

%description noanacron
Old style of {hourly,daily,weekly,monthly}.jobs without anacron. No features.

%prep
%setup -q

%build

%configure \
%if %{with pam}
--with-pam \
%endif
%if %{with selinux}
--with-selinux \
%endif
%if %{with audit}
--with-audit \
%endif
%if %{with inotify}
--with-inotify \
%endif
--enable-anacron --enable-pie

make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT DESTMAN=$RPM_BUILD_ROOT%{_mandir}
mkdir -pm700 $RPM_BUILD_ROOT%{_localstatedir}/spool/cron
mkdir -pm755 $RPM_BUILD_ROOT%{_initrddir}
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/
mkdir -pm755 $RPM_BUILD_ROOT%{_sysconfdir}/cron.d/
%if ! %{with pam}
    rm -f $RPM_BUILD_ROOT%{_sysconfdir}/pam.d/crond
%endif
install -m 755 cronie.init $RPM_BUILD_ROOT%{_initrddir}/crond
install -m 644 crond.sysconfig $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/crond
touch $RPM_BUILD_ROOT%{_sysconfdir}/cron.deny
install -m 644 contrib/anacrontab $RPM_BUILD_ROOT%{_sysconfdir}/anacrontab
install -c -m755 contrib/0hourly $RPM_BUILD_ROOT%{_sysconfdir}/cron.d/0hourly
mkdir -pm 755 $RPM_BUILD_ROOT%{_sysconfdir}/cron.hourly
install -c -m755 contrib/0anacron $RPM_BUILD_ROOT%{_sysconfdir}/cron.hourly/0anacron
mkdir -p $RPM_BUILD_ROOT/var/spool/anacron
touch $RPM_BUILD_ROOT/var/spool/anacron/cron.daily
touch $RPM_BUILD_ROOT/var/spool/anacron/cron.weekly
touch $RPM_BUILD_ROOT/var/spool/anacron/cron.monthly

# noanacron package
install -m 644 contrib/dailyjobs $RPM_BUILD_ROOT/%{_sysconfdir}/cron.d/dailyjobs

%clean
rm -rf $RPM_BUILD_ROOT

%post
/sbin/chkconfig --add crond

%post anacron
[ -e /var/spool/anacron/cron.daily ] || touch /var/spool/anacron/cron.daily
[ -e /var/spool/anacron/cron.weekly ] || touch /var/spool/anacron/cron.weekly
[ -e /var/spool/anacron/cron.monthly ] || touch /var/spool/anacron/cron.monthly

%preun
if [ "$1" = "0" ]; then
    service crond stop >/dev/null 2>&1 ||:
    /sbin/chkconfig --del crond
fi

%postun
if [ "$1" -ge "1" ]; then
    service crond condrestart > /dev/null 2>&1 ||:
fi

# empty /etc/crontab in case there are only old regular jobs
%triggerun -- cronie < 1.4.1
cp -a /etc/crontab /etc/crontab.rpmsave
sed -e '/^01 \* \* \* \* root run-parts \/etc\/cron\.hourly/d'\
  -e '/^02 4 \* \* \* root run-parts \/etc\/cron\.daily/d'\
  -e '/^22 4 \* \* 0 root run-parts \/etc\/cron\.weekly/d'\
  -e '/^42 4 1 \* \* root run-parts \/etc\/cron\.monthly/d' /etc/crontab.rpmsave > /etc/crontab
exit 0

#copy the lock, remove old daemon from chkconfig
%triggerun -- vixie-cron
cp -a /var/lock/subsys/crond /var/lock/subsys/cronie > /dev/null 2>&1 ||:

#if the lock exist, then we restart daemon (it was running in the past).
#add new daemon into chkconfig everytime, when we upgrade to cronie from vixie-cron
%triggerpostun -- vixie-cron
/sbin/chkconfig --add crond
[ -f /var/lock/subsys/cronie ] && ( rm -f /var/lock/subsys/cronie ; service crond restart ) > /dev/null 2>&1 ||:

%files
%defattr(-,root,root,-)
%doc AUTHORS COPYING INSTALL README ChangeLog
%attr(755,root,root) %{_sbindir}/crond
%attr(6755,root,root) %{_bindir}/crontab
%{_mandir}/man8/crond.*
%{_mandir}/man8/cron.*
%{_mandir}/man5/crontab.*
%{_mandir}/man1/crontab.*
%dir %{_localstatedir}/spool/cron
%dir %{_sysconfdir}/cron.d
%{_initrddir}/crond
%if %{with pam}
%attr(0644,root,root) %config(noreplace) %{_sysconfdir}/pam.d/crond
%endif
%config(noreplace) %{_sysconfdir}/sysconfig/crond
%config(noreplace) %{_sysconfdir}/cron.deny
%attr(0644,root,root) %{_sysconfdir}/cron.d/0hourly

%files anacron
%defattr(-,root,root,-)
%{_sbindir}/anacron
%attr(0755,root,root) %{_sysconfdir}/cron.hourly/0anacron
%config(noreplace) %{_sysconfdir}/anacrontab
%dir /var/spool/anacron
%ghost %verify(not md5 size mtime) /var/spool/anacron/cron.daily
%ghost %verify(not md5 size mtime) /var/spool/anacron/cron.weekly
%ghost %verify(not md5 size mtime) /var/spool/anacron/cron.monthly
%{_mandir}/man5/anacrontab.*
%{_mandir}/man8/anacron.*

%files noanacron
%defattr(-,root,root,-)
%attr(0644,root,root) %{_sysconfdir}/cron.d/dailyjobs

%changelog
* Thu Apr 22 2010 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.4-2
- remove patches because they were included in new release.
- 584006 lsb compliance
- upload correct source
- Resolves: bz#584006

* Fri Feb 19 2010 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.3-6
- CVE-2010-0424 Race condition by setting timestamp
- Resolves: rhbz#566501

* Fri Feb 12 2010 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.3-5
- add ISC license
- apply small fixes: anacrontab man page is more readable and
  values from /etc/security/pam_env.conf are used.
- Related: rhzb#543948

* Wed Jan 13 2010 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.3-4
- 554689 jobs from nfs homes weren't executed
- Related: rhbz#543948

* Tue Jan 12 2010 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.3-3
- rebuild with new audit-libs
- Related: rbhz#543948

* Thu Nov  5 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.3-2
- 533189 pam needs add a line and selinux needs defined one function

* Tue Nov  3 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.3-1
- 531963 and 532482 creating noanacron package

* Mon Oct 19 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.2-2
- 529632 service crond stop returns appropriate value

* Mon Oct 12 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.2-1
- new release

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 1.4.1-3
- rebuilt with new audit

* Fri Aug 14 2009 Tomas Mraz <tmraz@redhat.com> - 1.4.1-2
- create the anacron timestamps in correct post script

* Fri Aug 14 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.4.1-1
- update to 1.4.1
- create and own /var/spool/anacron/cron.{daily,weekly,monthly} to
 remove false warning about non existent files
- Resolves: 517398

* Wed Aug  5 2009 Tomas Mraz <tmraz@redhat.com> - 1.4-4
- 515762 move anacron provides and obsoletes to the anacron subpackage

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Mon Jul 20 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.4-2
- merge cronie and anacron in new release of cronie
- obsolete/provide anacron in spec

* Thu Jun 18 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.3-2
- 506560 check return value of access

* Mon Apr 27 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.3-1
- new release

* Fri Apr 24 2009 Marcela Mašláňová <mmaslano@redhat.com> - 1.2-8
- 496973 close file descriptors after exec

* Mon Mar  9 2009 Tomas Mraz <tmraz@redhat.com> - 1.2-7
- rebuild

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Tue Dec 23 2008 Marcela Mašláňová <mmaslano@redhat.com> - 1.2-5
- 477100 NO_FOLLOW was removed, reload after change in symlinked
  crontab is needed, man updated.

* Fri Oct 24 2008 Marcela Mašláňová <mmaslano@redhat.com> - 1.2-4
- update init script

* Thu Sep 25 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.2-3
- add sendmail file into requirement, cause it's needed some MTA

* Thu Sep 18 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.2-2
- 462252  /etc/sysconfig/crond does not need to be executable 

* Thu Jun 26 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.2-1
- update to 1.2

* Tue Jun 17 2008 Tomas Mraz <tmraz@redhat.com> - 1.1-3
- fix setting keycreate context
- unify logging a bit
- cleanup some warnings and fix a typo in TZ code
- 450993 improve and fix inotify support

* Wed Jun  4 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.1-2
- 49864 upgrade/update problem. Syntax error in spec.

* Wed May 28 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.1-1
- release 1.1

* Tue May 20 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-6
- 446360 check for lock didn't call chkconfig

* Tue Feb 12 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-5
- upgrade from less than cronie-1.0-4 didn't add chkconfig

* Wed Feb  6 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-4
- 431366 after reboot wasn't cron in chkconfig

* Tue Feb  5 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-3
- 431366 trigger part => after update from vixie-cron on cronie will 
	be daemon running.

* Wed Jan 30 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-2
- change the provides on higher version than obsoletes

* Tue Jan  8 2008 Marcela Maslanova <mmaslano@redhat.com> - 1.0-1
- packaging cronie
- thank's for help with packaging to my reviewers
