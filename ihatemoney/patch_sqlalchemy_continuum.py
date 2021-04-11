"""
A temporary work-around to patch SQLAlchemy-continuum per:
https://github.com/kvesteri/sqlalchemy-continuum/pull/242

Source code reproduced under their license:

    Copyright (c) 2012, Konsta Vesterinen

    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this
      list of conditions and the following disclaimer.

    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.

    * The names of the contributors may not be used to endorse or promote products
      derived from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
    INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
    BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
    LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
    OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
    ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sqlalchemy as sa
from sqlalchemy_continuum import Operation
from sqlalchemy_continuum.builder import Builder
from sqlalchemy_continuum.expression_reflector import VersionExpressionReflector
from sqlalchemy_continuum.relationship_builder import RelationshipBuilder
from sqlalchemy_continuum.utils import adapt_columns, option


class PatchedRelationShipBuilder(RelationshipBuilder):
    def association_subquery(self, obj):
        """
        Returns an EXISTS clause that checks if an association exists for given
        SQLAlchemy declarative object. This query is used by
        many_to_many_criteria method.

        Example query:

        .. code-block:: sql

        EXISTS (
            SELECT 1
            FROM article_tag_version
            WHERE article_id = 3
            AND tag_id = tags_version.id
            AND operation_type != 2
            AND EXISTS (
                SELECT 1
                FROM article_tag_version as article_tag_version2
                WHERE article_tag_version2.tag_id = article_tag_version.tag_id
                AND article_tag_version2.tx_id <=5
                AND article_tag_version2.article_id = 3
                GROUP BY article_tag_version2.tag_id
                HAVING
                    MAX(article_tag_version2.tx_id) =
                    article_tag_version.tx_id
            )
        )

        :param obj: SQLAlchemy declarative object
        """

        tx_column = option(obj, "transaction_column_name")
        join_column = self.property.primaryjoin.right.name
        object_join_column = self.property.primaryjoin.left.name
        reflector = VersionExpressionReflector(obj, self.property)

        association_table_alias = self.association_version_table.alias()
        association_cols = [
            association_table_alias.c[association_col.name]
            for _, association_col in self.remote_to_association_column_pairs
        ]

        association_exists = sa.exists(
            sa.select([1])
            .where(
                sa.and_(
                    association_table_alias.c[tx_column] <= getattr(obj, tx_column),
                    association_table_alias.c[join_column]
                    == getattr(obj, object_join_column),
                    *[
                        association_col
                        == self.association_version_table.c[association_col.name]
                        for association_col in association_cols
                    ],
                )
            )
            .group_by(*association_cols)
            .having(
                sa.func.max(association_table_alias.c[tx_column])
                == self.association_version_table.c[tx_column]
            )
            .correlate(self.association_version_table)
        )
        return sa.exists(
            sa.select([1])
            .where(
                sa.and_(
                    reflector(self.property.primaryjoin),
                    association_exists,
                    self.association_version_table.c.operation_type != Operation.DELETE,
                    adapt_columns(self.property.secondaryjoin),
                )
            )
            .correlate(self.local_cls, self.remote_cls)
        )


class PatchedBuilder(Builder):
    def build_relationships(self, version_classes):
        """
        Builds relationships for all version classes.

        :param version_classes: list of generated version classes
        """
        for cls in version_classes:
            if not self.manager.option(cls, "versioning"):
                continue

            for prop in sa.inspect(cls).iterate_properties:
                if prop.key == "versions":
                    continue
                builder = PatchedRelationShipBuilder(self.manager, cls, prop)
                builder()
