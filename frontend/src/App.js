import { BrowserRouter, Routes, Route } from "react-router-dom";
import PulseSurveyForm from "./PulseSurveyForm";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PulseSurveyForm />} />
        <Route path="/survey/:token" element={<PulseSurveyForm />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
