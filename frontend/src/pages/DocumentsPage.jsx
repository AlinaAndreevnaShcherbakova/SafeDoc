import React, { useEffect, useMemo, useState } from "react";
import Alert from "react-bootstrap/Alert";
import Badge from "react-bootstrap/Badge";
import Button from "react-bootstrap/Button";
import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Form from "react-bootstrap/Form";
import InputGroup from "react-bootstrap/InputGroup";
import Row from "react-bootstrap/Row";
import Stack from "react-bootstrap/Stack";
import Table from "react-bootstrap/Table";

import { api } from "../api/client";
import Loader from "../components/Loader";

const VISIBILITY_OPTIONS = ["by_request", "read_all", "edit_all"];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [uploadFile, setUploadFile] = useState(null);
  const [uploadComment, setUploadComment] = useState("");
  const [uploadVisibility, setUploadVisibility] = useState("by_request");
  const [uploading, setUploading] = useState(false);

  const [linkExpiresAt, setLinkExpiresAt] = useState("");
  const [lastPublicLink, setLastPublicLink] = useState("");

  const sortedDocs = useMemo(() => [...documents].sort((a, b) => b.id - a.id), [documents]);

  async function loadDocuments() {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/documents", { params: { search } });
      setDocuments(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось загрузить документы");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpload(event) {
    event.preventDefault();
    if (!uploadFile) {
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("visibility", uploadVisibility);
      if (uploadComment) {
        formData.append("comment", uploadComment);
      }
      await api.post("/documents", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadFile(null);
      setUploadComment("");
      await loadDocuments();
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    try {
      await api.delete(`/documents/${id}`);
      await loadDocuments();
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка удаления");
    }
  }

  async function handleDownload(id, name) {
    try {
      const response = await api.get(`/documents/${id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка скачивания");
    }
  }

  async function handleCreatePublicLink(id) {
    if (!linkExpiresAt) {
      setError("Укажи срок действия ссылки");
      return;
    }

    try {
      const { data } = await api.post(`/links/${id}`, {
        expires_at: new Date(linkExpiresAt).toISOString(),
      });
      const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;
      setLastPublicLink(`${baseUrl}/links/public/${data.token}`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка создания ссылки");
    }
  }

  return (
    <Stack gap={3}>
      <Card>
        <Card.Body>
          <Card.Title>Загрузка документа</Card.Title>
          <Form onSubmit={handleUpload}>
            <Row className="g-2">
              <Col md={4}>
                <Form.Control type="file" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} required />
              </Col>
              <Col md={3}>
                <Form.Select value={uploadVisibility} onChange={(e) => setUploadVisibility(e.target.value)}>
                  {VISIBILITY_OPTIONS.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </Form.Select>
              </Col>
              <Col md={3}>
                <Form.Control
                  placeholder="Комментарий"
                  value={uploadComment}
                  onChange={(e) => setUploadComment(e.target.value)}
                />
              </Col>
              <Col md={2}>
                <Button type="submit" className="w-100" disabled={uploading}>
                  {uploading ? "..." : "Загрузить"}
                </Button>
              </Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      <Card>
        <Card.Body>
          <Card.Title>Документы</Card.Title>
          <InputGroup className="mb-3">
            <Form.Control
              placeholder="Поиск по названию"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button variant="outline-secondary" onClick={loadDocuments}>
              Найти
            </Button>
          </InputGroup>

          <Row className="mb-3">
            <Col md={4}>
              <Form.Control
                type="datetime-local"
                value={linkExpiresAt}
                onChange={(e) => setLinkExpiresAt(e.target.value)}
              />
              <Form.Text>Срок действия для новой публичной ссылки</Form.Text>
            </Col>
          </Row>

          {error && <Alert variant="danger">{error}</Alert>}
          {lastPublicLink && (
            <Alert variant="success" className="small">
              Публичная ссылка: <a href={lastPublicLink}>{lastPublicLink}</a>
            </Alert>
          )}

          {loading ? (
            <Loader />
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя</th>
                  <th>MIME</th>
                  <th>Размер</th>
                  <th>Видимость</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {sortedDocs.map((doc) => (
                  <tr key={doc.id}>
                    <td>{doc.id}</td>
                    <td>{doc.name}</td>
                    <td className="small">{doc.mime}</td>
                    <td>{doc.size_bytes}</td>
                    <td>
                      <Badge bg="secondary">{doc.visibility}</Badge>
                    </td>
                    <td>
                      <Stack direction="horizontal" gap={2}>
                        <Button size="sm" variant="outline-primary" onClick={() => handleDownload(doc.id, doc.name)}>
                          Скачать
                        </Button>
                        <Button size="sm" variant="outline-success" onClick={() => handleCreatePublicLink(doc.id)}>
                          Ссылка
                        </Button>
                        <Button size="sm" variant="outline-danger" onClick={() => handleDelete(doc.id)}>
                          Удалить
                        </Button>
                      </Stack>
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
