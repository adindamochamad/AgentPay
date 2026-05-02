import { Component } from "react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { adaGalat: false, pesan: "" };
  }

  static getDerivedStateFromError(kesalahan) {
    return { adaGalat: true, pesan: kesalahan?.message || "Galat tidak diketahui" };
  }

  componentDidCatch(kesalahan, info) {
    if (import.meta.env.DEV) {
      console.error(kesalahan, info);
    }
  }

  render() {
    if (this.state.adaGalat) {
      return (
        <div className="mx-auto max-w-lg rounded-xl border border-rose-900/50 bg-rose-950/40 p-8 text-center">
          <h2 className="text-lg font-semibold text-rose-200">Terjadi kesalahan pada antarmuka</h2>
          <p className="mt-2 text-sm text-rose-300/90">{this.state.pesan}</p>
          <button
            type="button"
            className="btn-primary mt-6"
            onClick={() => window.location.reload()}
            aria-label="Muat ulang halaman"
          >
            Muat ulang
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
