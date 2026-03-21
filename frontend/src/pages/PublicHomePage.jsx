import React from "react";
import Button from "react-bootstrap/Button";
import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import { Link } from "react-router-dom";

export default function PublicHomePage() {
  return (
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card>
            <Card.Body>
              <h3 className="mb-3">SafeDoc</h3>
              <p className="text-muted">Платформа для защищенного хранения корпоративного контента и управления доступом.</p>
              <Button as={Link} to="/login">Перейти ко входу</Button>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}

