import React, { useState } from "react";
import Alert from "react-bootstrap/Alert";
import Button from "react-bootstrap/Button";
import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Form from "react-bootstrap/Form";
import Row from "react-bootstrap/Row";
import Stack from "react-bootstrap/Stack";

import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ProfilePage() {
  const { user, refreshMe } = useAuth();
  const [form, setForm] = useState({
    surname: user?.surname || "",
    name: user?.name || "",
    middle_name: user?.middle_name || "",
    department: user?.department || "",
    position: user?.position || "",
    email: user?.email || "",
  });

  const [pwd, setPwd] = useState({ current_password: "", new_password: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function setField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function saveProfile(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.patch("/auth/me", {
        ...form,
        middle_name: form.middle_name || null,
      });
      await refreshMe();
      setSuccess("Профиль успешно обновлен.");
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось обновить профиль");
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.post("/auth/change-password", pwd);
      setPwd({ current_password: "", new_password: "" });
      setSuccess("Пароль успешно изменен.");
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось изменить пароль");
    }
  }

  return (
    <Stack gap={3}>
      <Card>
        <Card.Body>
          <Card.Title>Личный кабинет</Card.Title>
          <Form onSubmit={saveProfile}>
            <Row className="g-2">
              <Col md={4}><Form.Control value={form.surname} onChange={(e) => setField("surname", e.target.value)} placeholder="Введите фамилию" required /></Col>
              <Col md={4}><Form.Control value={form.name} onChange={(e) => setField("name", e.target.value)} placeholder="Введите имя" required /></Col>
              <Col md={4}><Form.Control value={form.middle_name} onChange={(e) => setField("middle_name", e.target.value)} placeholder="Введите отчество (необязательно)" /></Col>
              <Col md={4}><Form.Control value={form.department} onChange={(e) => setField("department", e.target.value)} placeholder="Введите отдел" required /></Col>
              <Col md={4}><Form.Control value={form.position} onChange={(e) => setField("position", e.target.value)} placeholder="Введите должность" required /></Col>
              <Col md={4}><Form.Control type="email" value={form.email} onChange={(e) => setField("email", e.target.value)} placeholder="Введите email" required /></Col>
              <Col md={2}><Button type="submit" className="w-100">Сохранить</Button></Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      <Card>
        <Card.Body>
          <Card.Title>Изменение пароля</Card.Title>
          <Form onSubmit={changePassword}>
            <Row className="g-2">
              <Col md={4}><Form.Control type="password" value={pwd.current_password} onChange={(e) => setPwd((prev) => ({ ...prev, current_password: e.target.value }))} placeholder="Введите текущий пароль" required /></Col>
              <Col md={4}><Form.Control type="password" value={pwd.new_password} onChange={(e) => setPwd((prev) => ({ ...prev, new_password: e.target.value }))} placeholder="Введите новый пароль" required /></Col>
              <Col md={2}><Button type="submit" className="w-100">Изменить</Button></Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}
    </Stack>
  );
}

