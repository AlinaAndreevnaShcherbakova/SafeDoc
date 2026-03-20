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

  async function createUser(event) {
    event.preventDefault();
    setError("");
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
              <Col md={3}><Form.Control placeholder="Логин" value={form.login} onChange={(e) => updateField("login", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Пароль" type="password" value={form.password} onChange={(e) => updateField("password", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Фамилия" value={form.surname} onChange={(e) => updateField("surname", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Имя" value={form.name} onChange={(e) => updateField("name", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Отчество" value={form.middle_name} onChange={(e) => updateField("middle_name", e.target.value)} /></Col>
              <Col md={3}><Form.Control placeholder="Отдел" value={form.department} onChange={(e) => updateField("department", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Должность" value={form.position} onChange={(e) => updateField("position", e.target.value)} required /></Col>
              <Col md={3}><Form.Control placeholder="Email" type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} required /></Col>
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
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Логин</th>
                  <th>ФИО</th>
                  <th>Email</th>
                  <th>Superadmin</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.login}</td>
                    <td>{`${user.surname} ${user.name}`}</td>
                    <td>{user.email}</td>
                    <td>{user.is_superadmin ? "Да" : "Нет"}</td>
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
