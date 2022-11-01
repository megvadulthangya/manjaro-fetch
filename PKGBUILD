# Maintainer: Stefano Capitani <stefanoatmanjarodotorg>

pkgname='manjaro-iso-downloader'
pkgver=0.1
pkgrel=1
_commit=feb431bb6c04440d12327b981dcf496b9e740788
pkgdesc='Download last Official Manjaro Isos with integrity checker'
arch=('any')
url='https://gitlab.manjaro.org/ste74/manjaro-iso-downloader'
license=('GPL3')
depends=('yad' 'zenity' 'manjaro-icons' 'curl' 'wget' 'aria2' 'sed' 'gawk')
source=("$pkgname-$_commit.tar.gz::$url/-/archive/$_commit/$pkgname-$_commit.tar.gz")
sha256sums=('5a70ae45963b560e6a54778f1d71a2c152d7793053fd5eaae5429760b1a94564')

package() {
	
	cd $pkgname-$_commit
	install -Dm755 $pkgname.sh $pkgdir/usr/bin/$pkgname
	install -Dm644 $pkgname.desktop $pkgdir/usr/share/applications/$pkgname.desktop    

}



