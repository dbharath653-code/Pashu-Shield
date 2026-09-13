import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Keeps a single failing screen (map tiles, microphone, ML worker, …) from
 * blanking the whole application, which is what React does by default.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center">
        <div className="p-3 bg-red-50 text-red-600 rounded-full">
          <AlertTriangle size={28} />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-800">This screen failed to load</h2>
          <p className="text-sm text-gray-500 mt-1 max-w-md break-words">
            {error.message || "An unexpected error occurred."}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <RefreshCw size={16} /> Try again
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 text-sm font-medium bg-brandBlue text-white rounded-lg hover:bg-blue-600"
          >
            Reload application
          </button>
        </div>
      </div>
    );
  }
}
