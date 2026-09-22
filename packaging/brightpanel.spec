Name:           brightpanel
Version:        1.0.0
Release:        1%{?dist}
Summary:        Production-grade external monitor control suite for Fedora Linux

License:        MIT
URL:            https://github.com/subhadipshil/brightpanel-Fedora
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  systemd-rpm-macros

Requires:       ddcutil >= 1.4.0
Requires:       python3-gobject
Requires:       libadwaita >= 1.4.0
Requires:       gtk4 >= 4.12.0
Requires:       i2c-tools

Recommends:     gnome-shell >= 45.0

%description
BrightPanel gives Linux users seamless hardware control over external monitors
connected via HDMI, DisplayPort, or USB-C using DDC/CI protocol.

Features:
- Native Libadwaita / GTK4 control center matching GNOME design guidelines
- High-performance D-Bus session service preventing I2C bus lockup
- Safe debounced hardware write queue for smooth slider dragging
- Synchronized multi-display brightness slider
- GNOME Shell 45+ top-panel indicator and quick sliders
- Instant keyboard shortcut support via CLI ('brightpanel inc', 'brightpanel set')
- System Doctor auditing i2c-dev modules, permissions, and monitor capabilities

%prep
%autosetup

%build
%py3_build

%install
%py3_install

# Install udev rules
install -D -p -m 0644 packaging/45-ddcutil-i2c.rules %{buildroot}%{_udevrulesdir}/45-ddcutil-i2c.rules

# Install kernel module auto-load configuration
install -D -p -m 0644 packaging/i2c-dev.conf %{buildroot}%{_prefix}/lib/modules-load.d/i2c-dev.conf

# Install systemd user service
install -D -p -m 0644 packaging/brightpanel.service %{buildroot}%{_userunitdir}/brightpanel.service

# Install desktop file
install -D -p -m 0644 packaging/io.github.subhadipshil.brightpanel.desktop %{buildroot}%{_datadir}/applications/io.github.subhadipshil.brightpanel.desktop

# Install AppStream metainfo
install -D -p -m 0644 packaging/io.github.subhadipshil.brightpanel.metainfo.xml %{buildroot}%{_datadir}/metainfo/io.github.subhadipshil.brightpanel.metainfo.xml

# Install scalable application icon
install -D -p -m 0644 packaging/icons/io.github.subhadipshil.brightpanel.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.subhadipshil.brightpanel.svg

# Install GNOME extension
install -d %{buildroot}%{_datadir}/gnome-shell/extensions/brightpanel@subhadipshil.github.com
install -p -m 0644 extension/metadata.json %{buildroot}%{_datadir}/gnome-shell/extensions/brightpanel@subhadipshil.github.com/
install -p -m 0644 extension/extension.js %{buildroot}%{_datadir}/gnome-shell/extensions/brightpanel@subhadipshil.github.com/
install -p -m 0644 extension/stylesheet.css %{buildroot}%{_datadir}/gnome-shell/extensions/brightpanel@subhadipshil.github.com/

%post
%systemd_user_post brightpanel.service
/usr/bin/udevadm control --reload-rules >/dev/null 2>&1 || :
/usr/bin/udevadm trigger >/dev/null 2>&1 || :

%preun
%systemd_user_preun brightpanel.service

%postun
%systemd_user_postun_with_restart brightpanel.service

%files
%license LICENSE
%doc README.md
%{_bindir}/brightpanel
%{_bindir}/brightpanel-gui
%{python3_sitelib}/brightpanel/
%{python3_sitelib}/brightpanel-*.egg-info/
%{_udevrulesdir}/45-ddcutil-i2c.rules
%{_prefix}/lib/modules-load.d/i2c-dev.conf
%{_userunitdir}/brightpanel.service
%{_datadir}/applications/io.github.subhadipshil.brightpanel.desktop
%{_datadir}/metainfo/io.github.subhadipshil.brightpanel.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.subhadipshil.brightpanel.svg
%{_datadir}/gnome-shell/extensions/brightpanel@subhadipshil.github.com/

%changelog
* Tue Sep 22 2026 Subhadip Shil <subhadipshil1623@gmail.com> - 1.0.0-1
- Initial production release for Fedora Linux
