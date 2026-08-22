import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import NewMatch from "./pages/NewMatch";
import MatchDetail from "./pages/MatchDetail";
import Metrics from "./pages/Metrics";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="new" element={<NewMatch />} />
          <Route path="match/:id" element={<MatchDetail />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}