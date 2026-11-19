# Draft formula for wmxscott/homebrew-tap. Fill in sha256 once v1.0.1 is tagged:
#   curl -sL https://github.com/wmxscott/hotbar/archive/refs/tags/v1.0.1.tar.gz | shasum -a 256
class Hotbar < Formula
  include Language::Python::Virtualenv

  desc "Keyboard toolbar for tmux that opens your tools in popups"
  homepage "https://github.com/wmxscott/hotbar"
  url "https://github.com/wmxscott/hotbar/archive/refs/tags/v1.0.1.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"
  head "https://github.com/wmxscott/hotbar.git", branch: "main"

  depends_on "fzf"
  depends_on "python@3.14"
  depends_on "tmux"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "hotbar #{version}", shell_output("#{bin}/hotbar --version")
  end
end
