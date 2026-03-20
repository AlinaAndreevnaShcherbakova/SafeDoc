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

export default function RequestsPage() {
  const [myRequests, setMyRequests] = useState([]);
  const [inboxRequests, setInboxRequests] = useState([]);
  const [documentId, setDocumentId] = useState("");
  const [requestedRole, setRequestedRole] = useState("reader");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [my, inbox] = await Promise.all([
        api.get("/access/requests/my"),
        api.get("/access/requests/inbox").catch((err) => {
          if (err?.response?.status === 403) {
            return { data: [] };
          }
          throw err;
        }),
      ]);
      setMyRequests(my.data);
      setInboxRequests(inbox.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка загрузки заявок");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function createRequest(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/access/requests", {
        document_id: Number(documentId),
        requested_role: requestedRole,
        message: message || null,
      });
      setDocumentId("");
      setMessage("");
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось создать заявку");
    }
  }

  async function resolveRequest(id, approve) {
    try {
      await api.post(`/access/requests/${id}/resolve`, {
        approve,
        resolution_comment: null,
      });
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось обработать заявку");
    }
  }

  return (
    <Stack gap={3}>
      <Card>
        <Card.Body>
          <Card.Title>Запросить доступ</Card.Title>
          <Form onSubmit={createRequest}>
            <Row className="g-2">
              <Col md={3}>
                <Form.Control
                  placeholder="ID документа"
                  type="number"
                  value={documentId}
                  onChange={(e) => setDocumentId(e.target.value)}
                  required
                />
              </Col>
              <Col md={3}>
                <Form.Select value={requestedRole} onChange={(e) => setRequestedRole(e.target.value)}>
                  <option value="reader">reader</option>
                  <option value="editor">editor</option>
                  <option value="owner">owner</option>
                  <option value="guest">guest</option>
                </Form.Select>
              </Col>
              <Col md={4}>
                <Form.Control
                  placeholder="Комментарий"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </Col>
              <Col md={2}>
                <Button type="submit" className="w-100">
                  Отправить
                </Button>
              </Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading ? (
        <Loader />
      ) : (
        <>
          <Card>
            <Card.Body>
              <Card.Title>Мои заявки</Card.Title>
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Документ</th>
                    <th>Роль</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {myRequests.map((row) => (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td>{row.document_id}</td>
                      <td>{row.requested_role}</td>
                      <td>{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body>
              <Card.Title>Входящие заявки (если есть права)</Card.Title>
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Документ</th>
                    <th>Пользователь</th>
                    <th>Роль</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {inboxRequests.map((row) => (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td>{row.document_id}</td>
                      <td>{row.requester_id}</td>
                      <td>{row.requested_role}</td>
                      <td>
                        <Stack direction="horizontal" gap={2}>
                          <Button size="sm" variant="outline-success" onClick={() => resolveRequest(row.id, true)}>
                            Approve
                          </Button>
                          <Button size="sm" variant="outline-danger" onClick={() => resolveRequest(row.id, false)}>
                            Reject
                          </Button>
                        </Stack>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </>
      )}
    </Stack>
  );
}
