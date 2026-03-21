import React, { useEffect, useState } from "react";
import Alert from "react-bootstrap/Alert";
import Button from "react-bootstrap/Button";
import Card from "react-bootstrap/Card";
import Badge from "react-bootstrap/Badge";
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
  const [requestedPermissions, setRequestedPermissions] = useState(["preview"]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [grantDocumentId, setGrantDocumentId] = useState("");
  const [grantUserId, setGrantUserId] = useState("");
  const [grantPermissions, setGrantPermissions] = useState(["preview"]);

  const [revokeDocumentId, setRevokeDocumentId] = useState("");
  const [revokeUserId, setRevokeUserId] = useState("");

  const permissionOptions = [
    ["preview", "Предпросмотр"],
    ["download", "Скачивание"],
    //["edit", "Редактирование"],
    ["version_view", "Просмотр версий"],
    ["version_manage", "Работа с версиями"],
    ["access_manage", "Управление доступом"],
  ];

  function normalizePermissions(value) {
    const normalized = new Set(value);
    /*if (normalized.has("download") || normalized.has("edit") || normalized.has("version_view") || normalized.has("version_manage")) {
      normalized.add("preview");
    }*/
    if (normalized.has("version_manage")) {
      normalized.add("version_view");
    }
    return permissionOptions.map(([key]) => key).filter((key) => normalized.has(key));
  }

  function updatePermissionSelection(current, key, checked) {
    const draft = new Set(current);
    if (checked) {
      draft.add(key);
    } else {
      draft.delete(key);
    }
    return normalizePermissions(Array.from(draft));
  }

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
        requested_permissions: requestedPermissions,
        message: message || null,
      });
      setDocumentId("");
      setMessage("");
      setRequestedPermissions(["preview"]);
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

  async function grantAccess(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/access/grant", {
        document_id: Number(grantDocumentId),
        user_id: Number(grantUserId),
        permissions: grantPermissions,
      });
      setGrantDocumentId("");
      setGrantUserId("");
      setGrantPermissions(["preview"]);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось изменить доступ");
    }
  }

  async function revokeAccess(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/access/revoke", {
        document_id: Number(revokeDocumentId),
        user_id: Number(revokeUserId),
      });
      setRevokeDocumentId("");
      setRevokeUserId("");
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось отозвать доступ");
    }
  }

  return (
    <Stack gap={3}>
      <Card>
        <Card.Body>
          <Card.Title>Запрос доступа к документу</Card.Title>
          <Form onSubmit={createRequest}>
            <Row className="g-2">
              <Col md={3}>
                <Form.Control
                  placeholder="Укажите ID документа"
                  type="number"
                  value={documentId}
                  onChange={(e) => setDocumentId(e.target.value)}
                  required
                />
              </Col>
              <Col md={5}>
                <Card body>
                  <div className="small text-muted mb-2">Выберите уровни прав</div>
                  {permissionOptions.map(([key, label]) => (
                    <Form.Check
                      key={key}
                      type="checkbox"
                      id={`request-${key}`}
                      label={label}
                      checked={requestedPermissions.includes(key)}
                      onChange={(e) => setRequestedPermissions(updatePermissionSelection(requestedPermissions, key, e.target.checked))}
                    />
                  ))}
                </Card>
              </Col>
              <Col md={2}>
                <Form.Control
                  placeholder="Укажите комментарий"
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

      <Card>
        <Card.Body>
          <Card.Title>Управление доступом</Card.Title>
          <Row className="g-3">
            <Col md={7}>
              <Form onSubmit={grantAccess}>
                <Row className="g-2">
                  <Col md={3}>
                    <Form.Control
                      type="number"
                      placeholder="ID документа"
                      value={grantDocumentId}
                      onChange={(e) => setGrantDocumentId(e.target.value)}
                      required
                    />
                  </Col>
                  <Col md={3}>
                    <Form.Control
                      type="number"
                      placeholder="ID пользователя"
                      value={grantUserId}
                      onChange={(e) => setGrantUserId(e.target.value)}
                      required
                    />
                  </Col>
                  <Col md={4}>
                    <div className="border rounded p-2">
                      {permissionOptions.map(([key, label]) => (
                        <Form.Check
                          key={`grant-${key}`}
                          type="checkbox"
                          label={label}
                          checked={grantPermissions.includes(key)}
                          onChange={(e) => setGrantPermissions(updatePermissionSelection(grantPermissions, key, e.target.checked))}
                        />
                      ))}
                    </div>
                  </Col>
                  <Col md={2}>
                    <Button type="submit" className="w-100">Изменить</Button>
                  </Col>
                </Row>
              </Form>
            </Col>
            <Col md={5}>
              <Form onSubmit={revokeAccess}>
                <Row className="g-2">
                  <Col md={4}>
                    <Form.Control
                      type="number"
                      placeholder="ID документа"
                      value={revokeDocumentId}
                      onChange={(e) => setRevokeDocumentId(e.target.value)}
                      required
                    />
                  </Col>
                  <Col md={4}>
                    <Form.Control
                      type="number"
                      placeholder="ID пользователя"
                      value={revokeUserId}
                      onChange={(e) => setRevokeUserId(e.target.value)}
                      required
                    />
                  </Col>
                  <Col md={4}>
                    <Button type="submit" variant="outline-danger" className="w-100">Отозвать</Button>
                  </Col>
                </Row>
              </Form>
            </Col>
          </Row>
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
              {myRequests.length === 0 ? <Alert variant="light" className="mb-0">Вы еще не отправили ни одной заявки.</Alert> : (
                <Table responsive hover>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Документ</th>
                      <th>Права</th>
                      <th>Статус</th>
                      <th>Дата отправки</th>
                      <th>Кто обработал</th>
                    </tr>
                  </thead>
                  <tbody>
                    {myRequests.map((row) => (
                      <tr key={row.id}>
                        <td>{row.id}</td>
                        <td>{row.document_id}</td>
                        <td>
                          <Stack direction="horizontal" gap={1} className="flex-wrap">
                            {row.requested_permissions?.map((perm) => <Badge key={perm} bg="secondary">{perm}</Badge>)}
                          </Stack>
                        </td>
                        <td>{row.status_ru || row.status}</td>
                        <td>{new Date(row.created_at).toLocaleString("ru-RU")}</td>
                        <td>{row.resolved_by_login || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>

          <Card>
            <Card.Body>
              <Card.Title>Входящие заявки и история обработки</Card.Title>
              {inboxRequests.length === 0 ? <Alert variant="light" className="mb-0">Для вас пока нет входящих заявок.</Alert> : (
                <Table responsive hover>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Документ</th>
                      <th>Отправитель</th>
                      <th>Права</th>
                      <th>Статус</th>
                      <th>Создана</th>
                      <th>Обработана</th>
                      <th>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inboxRequests.map((row) => (
                      <tr key={row.id}>
                        <td>{row.id}</td>
                        <td>{row.document_id}</td>
                        <td>{row.requester_login || row.requester_id}</td>
                        <td>
                          <Stack direction="horizontal" gap={1} className="flex-wrap">
                            {row.requested_permissions?.map((perm) => <Badge key={perm} bg="secondary">{perm}</Badge>)}
                          </Stack>
                        </td>
                        <td>{row.status_ru || row.status}</td>
                        <td>{new Date(row.created_at).toLocaleString("ru-RU")}</td>
                        <td>{row.resolved_at ? `${new Date(row.resolved_at).toLocaleString("ru-RU")} (${row.resolved_by_login || "-"})` : "-"}</td>
                        <td>
                          {row.status === "pending" ? (
                            <Stack direction="horizontal" gap={2}>
                              <Button size="sm" variant="outline-success" onClick={() => resolveRequest(row.id, true)}>
                                Одобрить
                              </Button>
                              <Button size="sm" variant="outline-danger" onClick={() => resolveRequest(row.id, false)}>
                                Отклонить
                              </Button>
                            </Stack>
                          ) : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </>
      )}
    </Stack>
  );
}
