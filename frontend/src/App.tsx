import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { Dashboard } from "./pages/Dashboard";
import { Projects } from "./pages/Projects";
import { ProjectDetail } from "./pages/ProjectDetail";
import { NewProject } from "./pages/NewProject";
import { LiveRun } from "./pages/LiveRun";
import { Artifacts } from "./pages/Artifacts";
import { Agents } from "./pages/Agents";
import { SecurityCenter } from "./pages/SecurityCenter";
import { QACenter } from "./pages/QACenter";
import { ReviewCenter } from "./pages/ReviewCenter";
import { ModelLab } from "./pages/ModelLab";
import { Settings } from "./pages/Settings";
import { Login } from "./pages/Login";

export const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/new" element={<NewProject />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/live" element={<LiveRun />} />
        <Route path="/artifacts" element={<Artifacts />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/security" element={<SecurityCenter />} />
        <Route path="/qa" element={<QACenter />} />
        <Route path="/review" element={<ReviewCenter />} />
        <Route path="/model-lab" element={<ModelLab />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
