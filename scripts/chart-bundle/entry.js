// Apache ECharts: only the dashboard's chart types and SVG renderer.
import {init, version} from 'echarts/core';
import {LineChart, BarChart, PieChart} from 'echarts/charts';
import {GridComponent, TooltipComponent, AriaComponent} from 'echarts/components';
import {SVGRenderer} from 'echarts/renderers';
import {use} from 'echarts/core';
use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, AriaComponent, SVGRenderer]);
export {init, version};
