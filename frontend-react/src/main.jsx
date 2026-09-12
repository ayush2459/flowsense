import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { FlowSenseProvider } from "./context/FlowSenseContext";
import "./index.css";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <FlowSenseProvider>
        <App />
      </FlowSenseProvider>
    </BrowserRouter>
  </React.StrictMode>
);