import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Summary from './pages/Summary'
import Timeline from './pages/Timeline'
import Metrics from './pages/Metrics'
import LeaveCalendar from './pages/LeaveCalendar'
import AdminPanel from './pages/AdminPanel'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="summary" element={<Summary />} />
            <Route path="timeline" element={<Timeline />} />
            <Route path="metrics" element={<Metrics />} />
            <Route path="leave" element={<LeaveCalendar />} />
            <Route path="admin" element={<AdminPanel />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App

