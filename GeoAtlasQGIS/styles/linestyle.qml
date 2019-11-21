<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyLocal="1" hasScaleBasedVisibilityFlag="0" styleCategories="Symbology|Labeling|Rendering" maxScale="0" simplifyAlgorithm="0" version="3.4.4-Madeira" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyMaxScale="1" labelsEnabled="1" minScale="1e+08">
  <renderer-v2 enableorderby="0" type="singleSymbol" symbollevels="0" forceraster="0">
    <symbols>
      <symbol type="line" name="0" force_rhr="0" clip_to_extent="1" alpha="1">
        <layer locked="0" pass="0" enabled="1" class="SimpleLine">
          <prop v="square" k="capstyle"/>
          <prop v="5;2" k="customdash"/>
          <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
          <prop v="MM" k="customdash_unit"/>
          <prop v="0" k="draw_inside_polygon"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="35,35,255,255" k="line_color"/>
          <prop v="solid" k="line_style"/>
          <prop v="1" k="line_width"/>
          <prop v="MM" k="line_width_unit"/>
          <prop v="0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0" k="ring_filter"/>
          <prop v="0" k="use_custom_dash"/>
          <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="rule-based">
    <rules key="{bba86780-b4b1-4450-8526-e5a5d5d97b29}">
      <rule key="{d8842230-f828-403d-84a8-76b290146aac}">
        <settings>
          <text-style fontItalic="0" fontUnderline="0" fontSize="20" fontFamily="MS Shell Dlg 2" namedStyle="normal" isExpression="1" fontSizeUnit="Point" useSubstitutions="0" fontLetterSpacing="0" textOpacity="1" fontWordSpacing="0" previewBkgrdColor="#ffffff" fontCapitals="0" textColor="0,0,0,255" fontWeight="50" fontSizeMapUnitScale="3x:0,0,0,0,0,0" multilineHeight="1" fieldName="'A'" blendMode="0" fontStrikeout="0">
            <text-buffer bufferDraw="0" bufferColor="255,255,255,255" bufferJoinStyle="128" bufferNoFill="1" bufferBlendMode="0" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSize="1" bufferSizeUnits="MM" bufferOpacity="1"/>
            <background shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeSVGFile="" shapeType="0" shapeDraw="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeFillColor="255,255,255,255" shapeSizeY="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRotation="0" shapeSizeType="0" shapeBlendMode="0" shapeRadiiX="0" shapeOffsetY="0" shapeSizeX="0" shapeSizeUnit="MM" shapeOffsetX="0" shapeRadiiY="0" shapeOpacity="1" shapeBorderWidthUnit="MM" shapeOffsetUnit="MM" shapeBorderWidth="0" shapeRotationType="0" shapeJoinStyle="64"/>
            <shadow shadowOffsetDist="1" shadowOffsetUnit="MM" shadowDraw="0" shadowRadius="1.5" shadowUnder="0" shadowRadiusUnit="MM" shadowOpacity="0.7" shadowScale="100" shadowOffsetAngle="135" shadowOffsetGlobal="1" shadowColor="0,0,0,255" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowBlendMode="6" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusAlphaOnly="0"/>
            <substitutions/>
          </text-style>
          <text-format multilineAlign="4294967295" leftDirectionSymbol="&lt;" autoWrapLength="0" wrapChar="" useMaxLineLengthForAutoWrap="1" rightDirectionSymbol=">" plussign="0" placeDirectionSymbol="0" decimals="3" reverseDirectionSymbol="0" addDirectionSymbol="0" formatNumbers="0"/>
          <placement offsetUnits="MM" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" quadOffset="4" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" priority="5" repeatDistanceUnits="MM" placementFlags="10" offsetType="0" maxCurvedCharAngleIn="25" xOffset="0" maxCurvedCharAngleOut="-25" fitInPolygonOnly="0" placement="2" yOffset="0" preserveRotation="1" repeatDistance="0" centroidWhole="0" centroidInside="0" rotationAngle="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" distMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" dist="0"/>
          <rendering labelPerPart="0" obstacleFactor="1" upsidedownLabels="0" minFeatureSize="0" fontMaxPixelSize="10000" drawLabels="1" scaleMax="0" limitNumLabels="0" obstacleType="0" zIndex="0" maxNumLabels="2000" mergeLines="0" scaleMin="0" fontLimitPixelSize="0" obstacle="1" fontMinPixelSize="3" displayAll="0" scaleVisibility="0"/>
          <dd_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option type="Map" name="properties">
                <Option type="Map" name="PositionX">
                  <Option type="bool" name="active" value="true"/>
                  <Option type="QString" name="expression" value="$x_at(0)"/>
                  <Option type="int" name="type" value="3"/>
                </Option>
                <Option type="Map" name="PositionY">
                  <Option type="bool" name="active" value="true"/>
                  <Option type="QString" name="expression" value="$y_at(0)"/>
                  <Option type="int" name="type" value="3"/>
                </Option>
              </Option>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </dd_properties>
        </settings>
      </rule>
      <rule key="{3b326685-f55d-4184-9b11-b595134c7041}">
        <settings>
          <text-style fontItalic="0" fontUnderline="0" fontSize="20" fontFamily="MS Shell Dlg 2" namedStyle="normal" isExpression="1" fontSizeUnit="Point" useSubstitutions="0" fontLetterSpacing="0" textOpacity="1" fontWordSpacing="0" previewBkgrdColor="#ffffff" fontCapitals="0" textColor="0,0,0,255" fontWeight="50" fontSizeMapUnitScale="3x:0,0,0,0,0,0" multilineHeight="1" fieldName="'A\''" blendMode="0" fontStrikeout="0">
            <text-buffer bufferDraw="0" bufferColor="255,255,255,255" bufferJoinStyle="128" bufferNoFill="1" bufferBlendMode="0" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSize="1" bufferSizeUnits="MM" bufferOpacity="1"/>
            <background shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeSVGFile="" shapeType="0" shapeDraw="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeFillColor="255,255,255,255" shapeSizeY="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRotation="0" shapeSizeType="0" shapeBlendMode="0" shapeRadiiX="0" shapeOffsetY="0" shapeSizeX="0" shapeSizeUnit="MM" shapeOffsetX="0" shapeRadiiY="0" shapeOpacity="1" shapeBorderWidthUnit="MM" shapeOffsetUnit="MM" shapeBorderWidth="0" shapeRotationType="0" shapeJoinStyle="64"/>
            <shadow shadowOffsetDist="1" shadowOffsetUnit="MM" shadowDraw="0" shadowRadius="1.5" shadowUnder="0" shadowRadiusUnit="MM" shadowOpacity="0.7" shadowScale="100" shadowOffsetAngle="135" shadowOffsetGlobal="1" shadowColor="0,0,0,255" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowBlendMode="6" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusAlphaOnly="0"/>
            <substitutions/>
          </text-style>
          <text-format multilineAlign="4294967295" leftDirectionSymbol="&lt;" autoWrapLength="0" wrapChar="" useMaxLineLengthForAutoWrap="1" rightDirectionSymbol=">" plussign="0" placeDirectionSymbol="0" decimals="3" reverseDirectionSymbol="0" addDirectionSymbol="0" formatNumbers="0"/>
          <placement offsetUnits="MM" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" quadOffset="4" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" priority="5" repeatDistanceUnits="MM" placementFlags="10" offsetType="0" maxCurvedCharAngleIn="25" xOffset="0" maxCurvedCharAngleOut="-25" fitInPolygonOnly="0" placement="2" yOffset="0" preserveRotation="1" repeatDistance="0" centroidWhole="0" centroidInside="0" rotationAngle="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" distMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" dist="0"/>
          <rendering labelPerPart="0" obstacleFactor="1" upsidedownLabels="0" minFeatureSize="0" fontMaxPixelSize="10000" drawLabels="1" scaleMax="0" limitNumLabels="0" obstacleType="0" zIndex="0" maxNumLabels="2000" mergeLines="0" scaleMin="0" fontLimitPixelSize="0" obstacle="1" fontMinPixelSize="3" displayAll="0" scaleVisibility="0"/>
          <dd_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option type="Map" name="properties">
                <Option type="Map" name="PositionX">
                  <Option type="bool" name="active" value="true"/>
                  <Option type="QString" name="expression" value="$x_at(-1)"/>
                  <Option type="int" name="type" value="3"/>
                </Option>
                <Option type="Map" name="PositionY">
                  <Option type="bool" name="active" value="true"/>
                  <Option type="QString" name="expression" value="$y_at(-1)"/>
                  <Option type="int" name="type" value="3"/>
                </Option>
              </Option>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </dd_properties>
        </settings>
      </rule>
    </rules>
  </labeling>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <layerGeometryType>1</layerGeometryType>
</qgis>
