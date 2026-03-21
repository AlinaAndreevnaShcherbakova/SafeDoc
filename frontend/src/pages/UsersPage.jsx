import React, { useEffect, useState } from "react";
import Alert from "react-bootstrap/Alert";
import Button from "react-bootstrap/Button";
import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Form from "react-bootstrap/Form";
import Row from "react-bootstrap/Row";
import Stack from "react-bootstrap/Stack";
import Table from "react-bootstrap/Table";

import { api } from "../api/client";
import Loader from "../components/Loader";

const emptyForm = {
  login: "",
  password: "",
  surname: "",
  name: "",
  middle_name: "",
  department: "",
  position: "",
  email: "",
};

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadUsers() {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/users");
      setUsers(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось загрузить пользователей");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  function validateForm() {
    if (!/^[A-Za-z0-9]+$/.test(form.login)) {
      setError("Логин должен содержать только латинские буквы и цифры");
      return false;
    }

    const namePattern = /^[A-Za-zА-Яа-яЁё]+$/;
    if (!namePattern.test(form.surname) || !namePattern.test(form.name)) {
      setError("Фамилия и имя должны содержать только буквы");
      return false;
    }
    if (form.middle_name && !namePattern.test(form.middle_name)) {
      setError("Отчество должно содержать только буквы");
      return false;
    }

    return true;
  }

  async function createUser(event) {
    event.preventDefault();
    setError("");
    if (!validateForm()) {
      return;
    }
    try {
      await api.post("/users", {
        ...form,
        middle_name: form.middle_name || null,
        is_superadmin: false,
      });
      setForm(emptyForm);
      await loadUsers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка создания пользователя");
    }
  }

  async function deleteUser(userId) {
    setError("");
    try {
      await api.delete(`/users/${userId}`);
      await loadUsers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка удаления пользователя");
    }
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <Stack gap={3}>
      <Card>
        <Card.Body>
          <Card.Title>Создать пользователя</Card.Title>
          <Form onSubmit={createUser}>
            <Row className="g-2">
              <Col md={3}><Form.Control placeholder="Введите логин" value={form.login} onChange={(e) => updateField("login", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Введите пароль" type="password" value={form.password} onChange={(e) => updateField("password", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Введите фамилию" value={form.surname} onChange={(e) => updateField("surname", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Введите имя" value={form.name} onChange={(e) => updateField("name", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Введите отчество (необязательно)" value={form.middle_name} onChange={(e) => updateField("middle_name", e.target.value)} /></Col>
              <Col md={3}><Form.Control placeholder="Введите отдел" value={form.department} onChange={(e) => updateField("department", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Введите должность" value={form.position} onChange={(e) => updateField("position", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Введите email" type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} required /></Col>
              <Col md={2}><Button type="submit" className="w-100">Создать</Button></Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <Card.Body>
          <Card.Title>Список пользователей</Card.Title>
          {loading ? (
            <Loader />
          ) : users.length === 0 ? (
            <Alert variant="light" className="mb-0">Пользователи пока не добавлены.</Alert>
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Логин</th>
                  <th>ФИО</th>
                  <th>Отдел</th>
                  <th>Должность</th>
                  <th>Роль</th>
                  <th>Email</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.login}</td>
                    <td>{`${user.surname} ${user.name}`}</td>
                    <td>{user.department}</td>
                    <td>{user.position}</td>
                    <td>{user.role === "superadmin" ? "Суперадминистратор" : "Пользователь"}</td>
                    <td>{user.email}</td>
                    <td>
                      <Button size="sm" variant="outline-danger" onClick={() => deleteUser(user.id)}>
                        Удалить
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </Stack>
  );
}
