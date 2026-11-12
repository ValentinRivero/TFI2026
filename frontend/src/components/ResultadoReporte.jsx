import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import DesgloseEstados from './DesgloseEstados.jsx';
import OcupacionCanchas from './OcupacionCanchas.jsx';
import RankingHorarios from './RankingHorarios.jsx';
import ResumenReporte from './ResumenReporte.jsx';
import VisitasComplejo from './VisitasComplejo.jsx';

/**
 * Resultado completo del dashboard (presentación): resumen, desglose por estado, ocupación por cancha, ranking de
 * horarios y visitas. `dashboard` es la respuesta de Django y `visitas`, la consulta independiente a Node.
 */
export default function ResultadoReporte({ dashboard, visitas }) {
  return (
    <div>
      <ResumenReporte dashboard={dashboard} />
      <Row className="g-3">
        <Col lg={6}><DesgloseEstados conteos={dashboard.conteos} /></Col>
        <Col lg={6}><OcupacionCanchas ocupacion={dashboard.ocupacion} /></Col>
        <Col lg={6}><RankingHorarios ranking={dashboard.ranking_horarios} /></Col>
        <Col lg={6}><VisitasComplejo consulta={visitas} /></Col>
      </Row>
    </div>
  );
}
