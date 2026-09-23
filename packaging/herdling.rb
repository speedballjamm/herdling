# Homebrew formula. Lives in github.com/speedballjamm/homebrew-tap as Formula/herdling.rb;
# this copy is the source of truth. Bump url + sha256 on each release.
class Herdling < Formula
  desc "Learn Herdr by playing it: a game that coaches you inside a real Herdr"
  homepage "https://github.com/speedballjamm/herdling"
  url "https://github.com/speedballjamm/herdling/archive/refs/tags/v0.1.3.tar.gz"
  sha256 "SHA256"
  license "MIT"

  depends_on "python@3.14"

  def install
    libexec.install Dir["*"]
    (bin/"herdling").write <<~SH
      #!/bin/sh
      exec "#{Formula["python@3.14"].opt_bin}/python3.14" "#{libexec}/herdling" "$@"
    SH
  end

  def caveats
    <<~EOS
      herdling needs Herdr 0.9 or newer:
        brew install herdr
      Then run `herdling` from a plain terminal (not inside Herdr or tmux).
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/herdling --version")
  end
end
